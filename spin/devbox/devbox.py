import json
from pathlib import Path
from typing import Text

from spin import cluster, utils, settings, ssh


class Devbox(utils.ShellRunnerMixin):
    DEVBOX_YAML_FILE = settings.TEMPLATES_PATH / 'devbox' / 'app.yaml'
    # TODO: Dynamic ssh path?  This is coupled with the docker account that we're logging in as
    REMOTE_PUBLIC_KEY_FOLDER = '/root/.ssh/'

    def __init__(
            self,
            cluster: cluster.Cluster,
            public_key_file: Text,
            ssh_config_filename: Text=None,
            verbose=True,
    ):
        super().__init__(verbose)
        if not self.DEVBOX_YAML_FILE.exists():
            raise ValueError(f"DevBox YAML file, {self.DEVBOX_YAML_FILE} doesn't exist.")

        public_key_path = Path(public_key_file).expanduser()
        if not public_key_path.exists():
            raise ValueError(f"Public key file, {public_key_file} doesn't exist.")
        self.public_key_path = public_key_path
        self.public_key_name = Path(self.public_key_path).name

        if not cluster.exists():
            raise ValueError(f"Cluster, {cluster} does not exist.")

        if ssh_config_filename is None:
            ssh_mod = ssh.SshConfigModifier()
        else:
            ssh_mod = ssh.SshConfigModifier(config_filename=ssh_config_filename)
        self.ssh_config_modifier = ssh_mod

        # TODO: remove?
        self.key_creator = ssh.SshKeyCreater()

        self.pod_name = None

    def create(self):
        # kc apply app.yaml
        self._run(f"kubectl apply -f {self.DEVBOX_YAML_FILE}")
        # TODO: GET POD NAME
        # exitcode, self.pod_name, _ = self._run("""kubectl get po -l run=devbox --output=name | sed "s/pod\///g" """)
        _, pod_name, _ = self._run("""kubectl get po -l run=devbox --output=name """)
        self.pod_name = pod_name.strip()[4:]

        # append local id_rsa.pub into remote ~/.ssh/authorized_keys
        self._run(f'kubectl exec {self.pod_name} -- bash -c "mkdir -p {self.REMOTE_PUBLIC_KEY_FOLDER}"')
        remote_auth_keys_str = str(Path(self.REMOTE_PUBLIC_KEY_FOLDER) / 'authorized_keys')
        self._run(f'kubectl exec {self.pod_name} -- bash -c "touch {remote_auth_keys_str}"')
        public_key_contents = self.public_key_path.read_text()
        self._run(f'''kubectl exec {self.pod_name} -- bash -c "echo '{public_key_contents}' >> {remote_auth_keys_str}"''')

        # get devbox ip address
        _, out, _ = self._run('kubectl get svc my-service -o json')
        out = json.loads(out)
        ip = out['status']['loadBalancer']
        print(ip)

        # self.ssh_config_modifier.add_host_entry(
        #     # TODO: deal with devbox entry already exists
        #     host_tag='devbox',
        #     host_name=ip,
        # )

        # edit local ~/.ssh/config
        #     ######### start added by spin #########
        #     Host devbox
        #         ip: 123.123.123.123
        #         port: 22
        #         ForwardAgent: True
        #     ########## end added by spin ##########
        # set local context variables
        # print out ip address
        # print out ssh config modifications
        pass

    def delete(self):
        pass

    def exists(self):
        pass


if __name__ == '__main__':
    cluster = cluster.GkeCluster(
        name='my-cluster',
        zone='us-central1-a',
        master_machine_type='n1-standard-4',
        num_master_nodes=1,
        node_pools=(
            cluster.NodePool(
                name='gpu-workers',
                machine_type='n1-standard-4',
                accelerator='nvidia-tesla-k80',
                accelerator_count_per_node=1,
                min_nodes=0,
                num_nodes=1,
                max_nodes=10,
                preemptible=True,
            ),
            cluster.NodePool(
                name='workers',
                machine_type='n1-standard-4',
                accelerator=None,
                accelerator_count_per_node=0,
                min_nodes=0,
                num_nodes=0,
                max_nodes=10,
                preemptible=True,
            ),
        ),
        verbose=True,
    )
    import time
    tt = time.time()
    tc = time.clock()
    print(f"Starting at tt={tt}, tc={tc}")
    cluster.create()
    print(f"Took tt={time.time() - tt}, tc={time.clock() - tc}")

    db = Devbox(
        cluster=cluster,
        public_key_file='~/.ssh/id_rsa.pub',
    )
    db.create()

