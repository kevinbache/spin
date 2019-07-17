import abc
import json
import time
from typing import Iterable, Text

from spin import utils


class NodePool(utils.ShellRunnerMixin):
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
            command += ' --preemptible'

        if self.accelerator_count_per_node > 0:
            command += f' --accelerator=type={self.accelerator},count={self.accelerator_count_per_node}'

        print("nodepool.create command: {}".format(command))

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

    def list(self):
        command = f"""gcloud container node-pools list \
            --cluster={self.cluster.name} \
            --zone={self.cluster.zone} \
            --format="value(NAME)" """
        _, out, _ = self._run(command)
        return out.strip().split('\n')

    def exists(self):
        return self.name in self.list()


class Node(NodePool):
    def __init__(
            self,
            name='my-node',
            machine_type='n1-standard-4',
            accelerator='nvidia-tesla-k80',
            accelerator_count_per_node=1,
            allow_to_scale_to_zero=True,
            preemptible=True,
            verbose=True,
    ):
        super().__init__(
            name=name,
            machine_type=machine_type,
            accelerator=accelerator,
            accelerator_count_per_node=accelerator_count_per_node,
            min_nodes=0 if allow_to_scale_to_zero else 1,
            num_nodes=1,
            max_nodes=1,
            preemptible=preemptible,
            verbose=verbose,
        )


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


class GcloudHelper(utils.ShellRunnerMixin):
    def get_project(self):
        _, out, _ = self._run('gcloud config get-value project')
        return out.strip()

    def set_project(self, project_name: Text):
        self._run(f'gcloud config set project {project_name}')


class GkeCluster(Cluster, utils.ShellRunnerMixin):
    def __init__(
            self,
            project: Text,
            name='my-cluster',
            zone='us-central1-a',
            num_master_nodes=1,
            master_machine_type='n1-standard-4',
            members: Iterable[NodePool] = (),
            verbose=True,
            do_error_if_project_different=True,
    ):
        super().__init__()

        self.gcloud_helper = GcloudHelper()
        current_project = self.gcloud_helper.get_project()
        if current_project != project:
            if do_error_if_project_different:
                raise ValueError(f"Tried to create cluster with project {project} and "
                                 f"do_error_if_project_different=True but current gcloud project is {current_project}\n"
                                 f"You can change your gcloud project in python with "
                                 f"  GcloudHelper.set_project({project}) \n"
                                 f"or by running on the command line: \n"
                                 f"  gcloud config set project {project}")
            else:
                if self.verbose:
                    print(f"Changing project from {current_project} to {project}")
                self.gcloud_helper.set_project(project)

        self.project = project

        self.name = name
        self.zone = zone
        self.num_master_nodes = num_master_nodes
        self.master_machine_type = master_machine_type

        self.node_pools = {}
        for node_pool in members:
            self._add_node_pool(node_pool)

        self.verbose = verbose

    def __eq__(self, o: object) -> bool:
        return type(self) == type(o) and self.__dict__ == o.__dict__

    def __hash__(self) -> int:
        return hash(self.__dict__)

    def _add_node_pool(self, node_pool: NodePool):
        node_pool.set_cluster(self)
        self.node_pools[node_pool.name] = node_pool

    def create(self, error_if_exists=False, create_node_pools=True):
        # https://cloud.google.com/sdk/gcloud/reference/container/clusters/create
        # https://cloud.google.com/compute/docs/machine-types
        # 3:07 for cluster startup

        # if self.exists():
        #     if error_if_exists:
        #         raise ValueError(f"A cluster named {self.name} already exists.")
        #     else:
        #         # TODO: this is switching the global kubectl context to point to the current cluster.
        #         return self._run(f'gcloud container clusters get-credentials {self.name}')
        #
        # command = f"""gcloud container clusters create {self.name} \
        #     --zone={self.zone} \
        #     --num-nodes={self.num_master_nodes} \
        #     --machine-type={self.master_machine_type} \
        #     --enable-autoupgrade
        # """
        # print("cluster.create command: {}".format(command))
        # outs = [self._run(command)]

        outs = []
        if create_node_pools:
            for node_pool in self.node_pools.values():
                if self.verbose:
                    print(f"Creating node pool {node_pool} at {time.clock()}. ", end='')
                outs.append(node_pool.create())
                if self.verbose:
                    print("Done.")

        return outs

    def delete(self, do_async=True):
        command = f"gcloud container clusters delete {self.name} --zone={self.zone}"
        if do_async:
            command += ' --async'
        self._run(command)

    def exists(self) -> bool:
        command = f"""gcloud container clusters list --zone={self.zone} --format="value(NAME)" """
        exitcode, out, err = self._run(command)
        cluster_names = out.strip().split('\n')
        return self.name in cluster_names


# if __name__ == '__main__':
#     print(f'project: "{GcloudHelper().get_project()}"')
#
#     GcloudHelper().set_project('blah')
#     print(f'project: "{GcloudHelper().get_project()}"')
#
#     GcloudHelper().set_project('kb-experiment')
#     print(f'project: "{GcloudHelper().get_project()}"')
