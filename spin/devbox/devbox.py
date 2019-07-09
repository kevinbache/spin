import json
import re
from pathlib import Path
from typing import Text, Optional

from spin import cluster, utils, ssh, actions
from spin.devbox import kube_apply


def add_line_if_does_not_exist(filename: Text, line: Text):
    """Add the given line to the file unless it's already in the file."""
    with open(filename, 'a+') as f:
        lines = f.readlines()
        if line in lines:
            return
        else:
            f.writelines([line])
    return


class AddAuthorizedKey(actions.SingleValueAction):
    """Add a local public key to a remote authorized_keys file."""
    def __init__(
            self,
            local_public_key_filename: Text,
            remote_authorized_keys_location=str(Path('~/.ssh/authorized_keys').expanduser()),
    ):
        self.local_public_key_path = Path(local_public_key_filename).expanduser().resolve()
        self.remote_authorized_keys_location = remote_authorized_keys_location

        super().__init__(route='send_public_key')

    def _local_single_value(self) -> Text:
        return self.local_public_key_path.read_text()

    def _remote_single_value(self, value: Text) -> Optional[Text]:
        public_key_contents = value

        authorized_keys_path = Path(self.remote_authorized_keys_location)

        if not authorized_keys_path.parent.exists():
            authorized_keys_path.parent.mkdir(mode=0o755, parents=True)

        if not authorized_keys_path.exists():
            authorized_keys_path.touch(mode=0o644)

        add_line_if_does_not_exist(self.remote_authorized_keys_location, public_key_contents)

        return 'success'

    def _verify_on_client(self):
        if not self.local_public_key_path.exists():
            raise ValueError(f"Local public key path, {self.local_public_key_path} doesn't exist.")

        if not self.local_public_key_path.is_file():
            raise ValueError(f"Local public key path, {self.local_public_key_path} is not a file.")


class Devbox(utils.ShellRunnerMixin):
    DEVBOX_YAML_FILE = Path(__file__).parent / 'app.yaml_template'

    def __init__(
            self,
            cluster: cluster.GkeCluster,
            local_public_key_filename: Optional[Text]='~/.ssh/id_rsa.pub',
            local_ssh_config_filename: Text='~/.ssh/config',
            remote_authorized_keys_file: Text='~/.ssh/authorized_keys',
            namespace='spin',
            verbose=True,
    ):
        super().__init__(verbose)
        if not self.DEVBOX_YAML_FILE.exists():
            raise ValueError(f"DevBox YAML file, {self.DEVBOX_YAML_FILE} doesn't exist.")

        public_key_path = Path(local_public_key_filename).expanduser().resolve()
        if not public_key_path.exists():
            raise ValueError(f"Public key file, {local_public_key_filename} doesn't exist.")
        self.public_key_path = public_key_path
        self.public_key_name = Path(self.public_key_path).name

        if not cluster.exists():
            raise ValueError(f"Cluster, {cluster} does not exist.")

        self.cluster = cluster

        # ssh config modifier
        if local_ssh_config_filename is None:
            self.ssh_config_modifier = ssh.SshConfigModifier()
        else:
            self.ssh_config_modifier = ssh.SshConfigModifier(config_filename=local_ssh_config_filename)

        self.remote_authorized_keys_file = remote_authorized_keys_file
        self.namespace = namespace

        # server
        class DevBoxServer(actions.Server):
            def _set_actions(self):
                out = {}

                out['send_public_key'] = AddAuthorizedKey(local_public_key_filename)
                self.send_public_key = out['send_public_key']

                return out

        self.server = DevBoxServer(as_client=True)

        self.pod_name = None

    def _get_app_yaml(self, yaml_template_filename: Text):
        with open(yaml_template_filename, 'r') as f:
            return f.read().format(google_cloud_project=self.cluster.project)

    def create(self):
        kube_apply.from_yaml(self._get_app_yaml(self.DEVBOX_YAML_FILE), namespace=self.namespace)

        # TODO: GET POD NAME
        # exitcode, self.pod_name, _ = self._run("""kubectl get po -l run=devbox --output=name | sed "s/pod\///g" """)
        _, pod_name, _ = self._run("""kubectl get po -l run=devbox --output=name """)
        self.pod_name = pod_name.strip()[4:]

        self.server.send_public_key()

        # get devbox ip address
        _, out, _ = self._run('kubectl get svc ssh -o json')
        out = json.loads(out)
        ip = out['status']['loadBalancer']
        print(ip)

        private_key_filename = ssh.SshKeyCreator.get_private_from_pub(str(self.public_key_path))

        new_hosts_entry_str = self.ssh_config_modifier.add_host_entry(
            # TODO: deal with devbox entry already exists
            host_tag='devbox',
            host_name=ip,
            user='root',
            identity_file=private_key_filename,
            do_replace_existing_spin_hosts_entry=True,
        )

        if self.verbose:
            print(f"Started Devbox!")
            print(f"  Pod: {pod_name}")
            print(f"  ip:  {ip}")
            print("")
            print(f"Added the following host entry to SSH config at {str(self.ssh_config_modifier.config_path)}:")
            print(re.sub(r'\n', r'\n  ', new_hosts_entry_str))
            print("")
            print("You can ssh into it with the command:")
            print("  ssh root@devbox")
            print("")
            print("Or locally you can use Devbox.server to send it Actions.")

    def delete(self):
        self._run(f'kubectl delete deployment devbox')

    def exists(self):
        pass


if __name__ == '__main__':
    cluster = cluster.GkeCluster(
        project='kb-experiment',
        name='spin-cluster',
        zone='us-central1-a',
        master_machine_type='n1-standard-4',
        num_master_nodes=1,
        members=(
            cluster.NodePool(
                name='gpu-workers',
                machine_type='n1-standard-4',
                accelerator='nvidia-tesla-k80',
                accelerator_count_per_node=1,
                min_nodes=0,
                num_nodes=0,
                max_nodes=2,
                preemptible=False,
            ),
            cluster.NodePool(
                name='workers',
                machine_type='n1-standard-4',
                accelerator=None,
                accelerator_count_per_node=0,
                min_nodes=0,
                num_nodes=1,
                max_nodes=2,
                preemptible=True,
            ),
        ),
        verbose=True,
    )

    # with utils.Timer("Cluster creation"):
    #     cluster.create()

    db = Devbox(
        cluster=cluster,
    )
    db.create()

