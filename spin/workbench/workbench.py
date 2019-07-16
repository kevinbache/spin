from pathlib import Path
from typing import Text, List, Optional

from spin import utils, constants


class SshKey(utils.DictBouncer):
    PUB_SUFFIX = '.pub'

    def __init__(self, private_key_file: Text):
        super().__init__()
        self.private_key_path = Path(private_key_file)
        self.public_key_path = self.get_public_from_private(self.private_key_path)

    @classmethod
    def get_public_from_private(cls, private_key_path: Path):
        return Path(str(private_key_path) + cls.PUB_SUFFIX)

    @classmethod
    def get_private_from_public(cls, public_key_path: Path):
        if public_key_path.suffix != cls.PUB_SUFFIX:
            raise ValueError(f"Expected public key filename to end in .pub.  Got: {str(public_key_path)}.")
        return Path(str(public_key_path[:-4]))

    def exists(self, check_private_only=False, check_public_only=False):
        if check_private_only and check_public_only:
            raise ValueError("You should only set one of private_only and public_only but you set both.")

        out = True

        if not check_private_only:
            out &= self.public_key_path.exists()

        if not check_public_only:
            out &= self.private_key_path.exists()

        return out

    def read_public(self):
        if not self.exists(check_public_only=True):
            raise ValueError(f"Key at {str(self.public_key_path)} doesn't exist.")
        return open(str(self.public_key_path), 'r').read()

    def read_private(self):
        if not self.exists(check_private_only=True):
            raise ValueError(f"Key at {str(self.private_key_path)} doesn't exist.")
        return open(str(self.private_key_path), 'r').read()


class GithubRepo(utils.DictBouncer):
    def __init__(self, repo_url: Text, ssh_key: Optional[SshKey] = None):
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
    """Just a NodeConfig with sensible defaults for Google Cloud."""
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


class Workbench(utils.ShellRunnerMixin):
    SERVER_KEY_DIRECTORY = '/secrets/ssh_server_keys'
    USER_KEY_DIRECTORY = '/secrets/user_keys'
    USER_LOGIN_PUBLIC_KEYS_DIRECTORY = '/secrets/user_login_public_keys'

    def __init__(
            self,
            cloud_config: CloudConfig,
            master_node_config: NodeConfig,
            repos=List[GithubRepo],
            name='spin-workbench',
            kubernetes_namespace=constants.DEFAULT_KUBERNETES_NAMESPACE,
            ssh_login_key=SshKey,
            verbose=True,
    ):
        """
        A Workbench is, at its start, a Kubernetes cluster with a single machine in it.

        Args:
            cloud_config: config for the cloud where you'll launch this workbench
            master_node_config: the configuration for your workbench's master node
            repos: a list of repos to pull into your Workbench
            name: the name of this workbench
            kubernetes_namespace: the namespace in which to launch this workbench
            ssh_login_key: the ssh key on your computer which you'll use to login to this workbench
            # verbose: if True, print out status messages as you go
        """
        super().__init__(verbose)
        self.cloud_config = cloud_config
        self.master_node_config = master_node_config
        self.repos = repos
        self.name = name
        self.kubernetes_namespace = kubernetes_namespace

        self.ssh_login_key = ssh_login_key



    def add_key_as_secret(self, secret_directory_name: Text, key: SshKey):
        cmd = f'kubectl create secret generic {secret_directory_name} ' \
            f'--from-file={str(key.public_key_path)} --from-file={str(key.private_key_path)}'
        self._run(cmd)
        # kubectl create secret generic db-user-pass --from-file=./username.txt --from-file=./password.txt


        """
        on launch:
            generate server keys
            set login key
            add server keys to known_hosts.
            kube launch deployment
            kube launch service
        """

        """
        apiVersion: v1
        kind: Pod
        metadata:
          name: mypod
        spec:
          containers:
          - name: mypod
            image: redis
            volumeMounts:
            - name: foo
              mountPath: "/etc/foo"
              readOnly: true
          volumes:
          - name: foo
            secret:
              secretName: mysecret
              items:
              - key: username
                path: my-group/my-username
        """

