import tempfile
import time
from pathlib import Path
from typing import Text, List, Optional, Tuple, Dict

from spin import utils, constants, kubes, ssh
from spin.ssh import SshKeyOnDisk


class GithubRepo(utils.DictBouncer):
    def __init__(self, repo_url: Text, ssh_key: Optional[SshKeyOnDisk] = None):
        """
        Represents a github repo.

        Args:
            repo_url:
                e.g. git@github.com:your_github_username/your_github_repo_name.git
            ssh_key:
                The SSH key that you use to connect to github.  Only required if the repo is private.
        """
        super().__init__()
        self.repo_url = repo_url
        self.ssh_key = ssh_key


class CloudConfig(utils.DictBouncer):
    def __init__(self, cloud_project: Text, zone: Text):
        super().__init__()
        self.cloud_project = cloud_project
        self.zone = zone


class NodeConfig(utils.DictBouncer):
    def __init__(self, machine_type: Text, accelerator_type: Text, accelerator_count: int = 1):
        super().__init__()
        self.machine_type = machine_type
        self.accelerator_type = accelerator_type
        self.accelerator_count = accelerator_count


class GCloudNodeConfig(NodeConfig):
    """A NodeConfig with sensible defaults for Google Cloud."""
    def __init__(
            self,
            machine_type='n1-standard-4',
            accelerator_type='nvidia-tesla-k80',
            accelerator_count=1,
    ):
        super().__init__(
            machine_type=machine_type,
            accelerator_type=accelerator_type,
            accelerator_count=accelerator_count
        )


_DEFAULT_MASTER_NODE_CONFIG = GCloudNodeConfig()


class Workbench(utils.ShellRunnerMixin):
    class SecretType:
        """Simple holder to organize secret type info

        secret_type_str:    'ssh-server-keys'
        secret_name:        'my-workbench-ssh-server-keys'
        secret_mountpoint:  '/secrets/ssh-server-keys/'
        """
        def __init__(self, secret_type_str: Text):
            self.secret_type_str = secret_type_str

        def get_secret_name(self, workbench_name: Text):
            return f'{workbench_name}-{self.secret_type_str}'

        def get_secret_mountpoint(self):
            return f'/secrets/{self.secret_type_str}'

    SERVER_KEY_SECRET_TYPE = SecretType('ssh-server-keys')
    USER_KEY_SECRET_TYPE = SecretType('user-keys')
    USER_LOGIN_PUBLIC_KEYS_SECRET_TYPE = SecretType('user-login-public-keys')

    DEFAULT_CONTAINER_IMAGE_URI = 'gcr.io/kb-experiment/workbench:latest'

    def __init__(
            self,
            cloud_config: CloudConfig,
            repos: List[GithubRepo],
            ssh_login_key: SshKeyOnDisk,
            name='spin-workbench',
            master_node_config: NodeConfig = _DEFAULT_MASTER_NODE_CONFIG,
            kubernetes_namespace=constants.DEFAULT_KUBERNETES_NAMESPACE,
            container_image_uri=DEFAULT_CONTAINER_IMAGE_URI,
            verbose=True,
    ):
        """
        A Workbench is, at its start, a Kubernetes cluster with a single machine in it.

        Args:
            cloud_config: config for the cloud where you'll launch this workbench
            repos: a list of repos to pull into your Workbench
            name: the name of this workbench
            master_node_config: the configuration for your workbench's master node
            kubernetes_namespace: the namespace in which to launch this workbench
            ssh_login_key: the ssh key on your computer which you'll use to login to this workbench
            verbose: if True, print out status messages as you go
        """
        super().__init__(verbose)
        self.cloud_config = cloud_config
        self.master_node_config = master_node_config
        self.repos = repos
        self.name = name
        self.kubernetes_namespace = kubernetes_namespace
        self.container_image_uri = container_image_uri
        self.ssh_login_key = ssh_login_key
        
        self._secrets = []
        self._service = None
        self._deployment = None

    def _create_ssh_server_keys_as_secret(
            self,
            key_types=('dsa', 'rsa', 'ecdsa', 'ed25519'),
    ) -> Tuple[kubes.KubernetesSecret, Dict[Text, ssh.SshKeyInMemory]]:
        """Create a Kubernetes secret containing newly generated SSH keys of the given type.
        Used as SSH server keys on the workbench.

        Args:
            key_types: the ssh key types to create and add to the secret.

        Returns:
            Reference to a kubernetes secret which has already been created and which contains
            the requested private and public keys as members.
        """

        utils.ensure_cmdline_program_exists('ssh-keygen')

        key_type_to_in_memory_key = {}

        with tempfile.TemporaryDirectory() as tempdir:
            ssh_keys = []
            for key_type in key_types:
                private_key_location = f'{tempdir}/ssh_host_{key_type}_key'
                cmd = f'ssh-keygen -t {key_type} -N "" -f {private_key_location} -C ""'
                self._run(cmd)
                ssh_key = ssh.SshKeyOnDisk(private_key_location)
                if not ssh_key.exists():
                    raise IOError(f"Error creating key at location {private_key_location}")
                ssh_keys.append(ssh_key)
                key_type_to_in_memory_key[key_type] = ssh.SshKeyInMemory(ssh_key)
            # self._add_keys_as_secret(self.SERVER_KEY_SECRET_TYPE.get_secret_name(self.name), ssh_keys)
            secret = kubes.KubernetesSecret.from_ssh_keys(
                secret_name=self.SERVER_KEY_SECRET_TYPE.get_secret_name(self.name),
                mount_point_on_pod=self.SERVER_KEY_SECRET_TYPE.get_secret_mountpoint(),
                ssh_keys=ssh_keys,
            )
            # delete old secret if it already eixsts and create a new one
            secret.delete()
            secret.create()

        return secret, key_type_to_in_memory_key

    def create(self):
        # create SSH server keys as kubernetes secret.  these allow the workbench to run an SSH server
        server_keys_secret, ssh_key_type_to_in_memory_key = self._create_ssh_server_keys_as_secret()
        self._secrets.append(server_keys_secret)

        # create SSH user keys as kubernetes secret.  these allow the workbench to pull private repos
        user_keys = []
        for repo in self.repos:
            if repo.ssh_key is not None:
                user_keys.append(repo.ssh_key)
        user_keys_secret = kubes.KubernetesSecret.from_ssh_keys(
            secret_name=self.USER_KEY_SECRET_TYPE.get_secret_name(self.name),
            mount_point_on_pod=self.USER_KEY_SECRET_TYPE.get_secret_mountpoint(),
            ssh_keys=user_keys,
        )
        user_keys_secret.delete()
        user_keys_secret.create()
        self._secrets.append(user_keys_secret)

        # create login key as kubernetes secret.  this allows the user to ssh in to the workbench
        login_keys_secret = kubes.KubernetesSecret.from_ssh_keys(
            secret_name=self.USER_LOGIN_PUBLIC_KEYS_SECRET_TYPE.get_secret_name(self.name),
            mount_point_on_pod=self.USER_LOGIN_PUBLIC_KEYS_SECRET_TYPE.get_secret_mountpoint(),
            ssh_keys=[self.ssh_login_key],
        )
        login_keys_secret.delete()
        login_keys_secret.create()
        self._secrets.append(login_keys_secret)

        # launch the app to kubernetes
        self._service, self._deployment = kubes.get_service_and_deployment(
            deployment_name=self.name,
            container_image_uri=self.container_image_uri,
            service_name=self.name,
            ports=[
                kubes.KubernetesPort(name='ssh', external_port=22, pod_port=22),
                kubes.KubernetesPort(name='http', external_port=80, pod_port=80),
            ],
            secrets=self._secrets,
            num_deployment_replicas=1,
        )

        # always create your service before your deployment
        self._service.create()
        self._deployment.create()

        # TODO: really, we'd like this to be assigned a static DNS name.
        #   my-workbench.my-username.my-project.cloud.google.com or something.
        #   the reason is that then the user wouldn't have to reconfigure their IDE every time they shut down
        #   their workbench.
        #   we could run a service which would map workbench ip to that statically assigned name.
        ip, ports_dict = self._service.get_ip_and_ports()

        ssh_port_num = ports_dict['ssh']

        known_hosts_modifier = ssh.KnownHostsModifier()
        if self.verbose:
            print(f"Adding workbench's line to {known_hosts_modifier.known_hosts_file}")

        for ssh_key in ssh_key_type_to_in_memory_key.values():
            known_hosts_line = ssh_key.get_known_hosts_line(ip, ssh_port_num)
            known_hosts_modifier.add_known_host(known_hosts_line)

        config_modifier = ssh.SshConfigModifier()
        config_modifier.add_host_entry(
            host_tag=self.name,
            host_name=ip,
            user='root',
            port=ssh_port_num,
            identity_file=self.ssh_login_key.private_key_path,
            forward_agent=True,
            do_replace_existing_spin_hosts_entry=False,
        )

        if self.verbose:
            ports_str = '\n        '.join([f'{k}: {v}' for k, v in ports_dict.items()])

            # port = ports_dict['ssh']
            # port_str = '' if port == 22 else '-p {port}'
            # ssh_str = f"ssh root@{ip} {port_str}"
            ssh_str = f'ssh {self.name}'

            print(f"""
    Your workbench, {self.name}, has been created using container at {self.container_image_uri}  
    It has an IP address of {ip} and opens the following ports:
        {ports_str}
    
    You can ssh into it with the following command:
        {ssh_str} 
    """)


if __name__ == '__main__':
    ssh_key = SshKeyOnDisk('~/.ssh/id_rsa')
    wb = Workbench(
        cloud_config=CloudConfig(cloud_project='kb-experirment', zone='us-central1-a'),
        repos=[GithubRepo(repo_url='git@github.com:kevinbache/spin.git', ssh_key=ssh_key)],
        ssh_login_key=ssh_key,
        name='spin-workbench8',
    )
    wb.create()

