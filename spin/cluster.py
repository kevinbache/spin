import abc
from typing import Text, Iterable

from spin.utils import CommandLineInterfacerMixin


class NodePoolConfig:
    def __init__(
            self,
            name='my-pool',
            machine_type='n1-standard-4',
            accelerator='nvidia-tesla-k80',
            accelerator_count_per_node=1,
            min_nodes=0,
            num_nodes=1,
            max_nodes=5,
            preemptible=True,
    ):
        self.name = name
        self.machine_type = machine_type
        self.accelerator = accelerator
        self.accelerator_count_per_node = accelerator_count_per_node
        self.min_workers = min_nodes
        self.num_workers = num_nodes
        self.max_workers = max_nodes
        self.preemptible = preemptible

    def __eq__(self, o: object) -> bool:
        return type(self) == type(o) and self.__dict__ == o.__dict__

    def __hash__(self) -> int:
        return hash(self.__dict__)

    def _get_create_command(self, cluster_name: Text):
        command = f'''gcloud container node-pools create {self.name} \
            --cluster={cluster_name} \
            --machine-type={self.machine_type} \
            --min-nodes={self.min_nodes} \
            --num-nodes={self.num_nodes} \
            --max-nodes={self.max_nodes} \
            --zone={self.zone}
        '''

        if self.preemptible:
            command += ' \ \n --preemptible'

        if self.accelerator_count_per_node > 0:
            command += f' \ \n --accelerator=type={self.accelerator},count={self.accelerator_count_per_node}'

        return command


class ClusterDoerInterface(abc.ABC):
    @abc.abstractmethod
    def create_cluster(
            self,
            cluster_name='my-cluster',
            num_nodes=1,
            machine_type='n1-standard-8',
    ):
        pass

    @abc.abstractmethod
    def add_node_pool(self, config: NodePoolConfig):
        pass

    @abc.abstractmethod
    def resize_node_pool(self, name: Text, min_workers: int, num_workers: int, max_workers: int):
        pass


class GkeClusterDoer(ClusterDoerInterface, CommandLineInterfacerMixin):
    def __init__(
            self,
            cluster_name='my-cluster',
            zone='us-central1-a',
            master_machine_type='n1-standard-4',
            num_master_nodes=1,
            node_pool_configs: Iterable[NodePoolConfig]=(),
            verbose=True,
    ):
        super().__init__()

        self.cluster_name = cluster_name
        self.zone = zone
        self.master_machine_type = master_machine_type
        self.num_master_nodes = num_master_nodes

        self.node_pool_configs = {c.name: c for c in node_pool_configs}

        self.verbose = verbose

    def __eq__(self, o: object) -> bool:
        return type(self) == type(o) and self.__dict__ == o.__dict__

    def __hash__(self) -> int:
        return hash(self.__dict__)

    def create_cluster(
            self,
            cluster_name=None,
            zone=None,
            num_nodes=None,
            machine_type=None,
    ):
        # https://cloud.google.com/sdk/gcloud/reference/container/clusters/create
        # https://cloud.google.com/compute/docs/machine-types

        cluster_name = cluster_name or self.cluster_name
        zone = zone or self.zone
        num_nodes = num_nodes or self.num_master_nodes
        machine_type = machine_type or self.master_machine_type

        # 3:07 for cluster startup

        command = f"""gcloud container clusters create {cluster_name} \
            --zone {zone} \
            --num-nodes {num_nodes} \
            --machine-type={machine_type} \
            --enable-autoupgrade \
            --enable-autoscaling
        """
        return self._run(command)

    def does_cluster_exist(self, cluster_name=None, zone=None) -> bool:
        cluster_name = cluster_name or self.cluster_name
        zone = zone or self.zone
        command = f"""gcloud container clusters list --zone={zone} --format="value(NAME)" """
        exitcode, out, err = self._run(command)
        cluster_names = out.strip().split('\n')
        return cluster_name in cluster_names

    def add_node_pool(self, config: NodePoolConfig):
        # https://cloud.google.com/sdk/gcloud/reference/container/clusters/create
        # https://cloud.google.com/compute/docs/machine-types
        # https://cloud.google.com/kubernetes-engine/docs/tutorials/migrating-node-pool
        command = config._get_create_command(self.cluster_name)
        return self._run(command)

    def resize_node_pool(self, pool_name: Text, min_nodes: int, num_nodes: int, max_nodes: int):
        command = f'''gcloud container clusters resize {self.cluster_name} \
            --node-pool {pool_name} \
            --min-nodes {min_nodes} \
            --num-nodes {num_nodes} \
            --max-nodes {max_nodes} 
        '''
        return self._run(command)

