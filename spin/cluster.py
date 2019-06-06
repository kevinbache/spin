import abc
from typing import Text, Iterable

from spin.utils import CommandLineInterfacerMixin


class NodePool(CommandLineInterfacerMixin):
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
            verbose=True,
    ):
        super().__init__(verbose)
        self.name = name
        self.machine_type = machine_type
        self.accelerator = accelerator
        self.accelerator_count_per_node = accelerator_count_per_node
        self.min_nodes = min_nodes
        self.num_nodes = num_nodes
        self.max_nodes = max_nodes
        self.preemptible = preemptible

        self.cluster = None

    def __eq__(self, o: object) -> bool:
        return type(self) == type(o) and self.__dict__ == o.__dict__

    def __hash__(self) -> int:
        return hash(self.__dict__)

    def set_cluster(self, cluster: 'GkeCluster'):
        self.cluster = cluster

    def create(self, error_if_exists=False):
        # https://cloud.google.com/sdk/gcloud/reference/container/clusters/create
        # https://cloud.google.com/compute/docs/machine-types
        # https://cloud.google.com/kubernetes-engine/docs/tutorials/migrating-node-pool
        if self.cluster is None:
            raise ValueError("Cluster is not set.")

        if self.exists():
            if error_if_exists:
                raise ValueError(f"A node pool named {self.name} already exists.")
            else:
                return 0, None, None

        command = f'''gcloud container node-pools create {self.name} \
            --cluster={self.cluster.name} \
            --machine-type={self.machine_type} \
            --min-nodes={self.min_nodes} \
            --num-nodes={self.num_nodes} \
            --max-nodes={self.max_nodes} \
            --zone={self.cluster.zone}
        '''

        if self.preemptible:
            command += ' \ \n --preemptible'

        if self.accelerator_count_per_node > 0:
            command += f' \ \n --accelerator=type={self.accelerator},count={self.accelerator_count_per_node}'

        return self._run(command)

    def delete(self, do_async=True):
        command = f"""gcloud container node-pools delete {self.cluster.name} \
            --cluster {self.cluster.name} \
            --zone={self.cluster.zone}"""
        if do_async:
            command += ' \ \n --async'
        self._run(command)

    def resize(self):
        if self.cluster is None:
            raise ValueError("Cluster is not set.")

        command = f'''gcloud container clusters resize {self.cluster.name} \
            --node-pool {self.name} \
            --min-nodes {self.min_nodes} \
            --num-nodes {self.num_nodes} \
            --max-nodes {self.max_nodes} 
        '''
        return self._run(command)

    def exists(self):
        command = f"""gcloud container node-pools list \
            --cluster={self.cluster.name} \
            --zone={self.cluster.zone} \
            --format="value(NAME)" """
        exitcode, out, err = self._run(command)
        pool_names = out.strip().split('\n')
        return self.name in pool_names


class Cluster(abc.ABC):
    @abc.abstractmethod
    def create(self):
        pass

    @abc.abstractmethod
    def delete(self):
        pass

    @abc.abstractmethod
    def exists(self):
        pass


class GkeCluster(Cluster, CommandLineInterfacerMixin):
    def __init__(
            self,
            cluster_name='my-cluster',
            zone='us-central1-a',
            num_master_nodes=1,
            master_machine_type='n1-standard-4',
            node_pools: Iterable[NodePool] = (),
            verbose=True,
    ):
        super().__init__()

        self.cluster_name = cluster_name
        self.zone = zone
        self.num_master_nodes = num_master_nodes
        self.master_machine_type = master_machine_type

        self.node_pools = {}
        for node_pool in node_pools:
            self._add_node_pool(node_pool)

        self.verbose = verbose

    def __eq__(self, o: object) -> bool:
        return type(self) == type(o) and self.__dict__ == o.__dict__

    def __hash__(self) -> int:
        return hash(self.__dict__)

    def _add_node_pool(self, node_pool: NodePool):
        node_pool.set_cluster(self)
        self.node_pools[node_pool.name] = node_pool

    def create(self, error_if_exists=False):
        # https://cloud.google.com/sdk/gcloud/reference/container/clusters/create
        # https://cloud.google.com/compute/docs/machine-types
        # 3:07 for cluster startup

        if self.exists():
            if error_if_exists:
                raise ValueError(f"A cluster named {self.cluster_name} already exists.")
            else:
                return 0, None, None

        command = f"""gcloud container clusters create {self.cluster_name} \
            --zone={self.zone} \
            --num-nodes={self.num_master_nodes} \
            --machine-type={self.master_machine_type} \
            --enable-autoupgrade \
            --enable-autoscaling
        """
        return self._run(command)

    def delete(self, do_async=True):
        command = f"gcloud container clusters delete {self.cluster_name} --zone={self.zone}"
        if do_async:
            command += ' --async'
        self._run(command)

    def exists(self) -> bool:
        command = f"""gcloud container clusters list --zone={self.zone} --format="value(NAME)" """
        exitcode, out, err = self._run(command)
        cluster_names = out.strip().split('\n')
        return self.cluster_name in cluster_names
