from pathlib import Path

from spin.cluster import GkeCluster, NodePool
from spin.spin_config import ProjectConfig

PACKAGE_ROOT_PATH = Path(__file__).resolve().parent

PROJECT_ROOT_PATH = PACKAGE_ROOT_PATH / '..'
TESTS_PATH = PROJECT_ROOT_PATH / 'test'

SPIN_SETTINGS = ProjectConfig(
    cluster=GkeCluster(
        cluster_name='my-cluster',
        zone='us-central1-a',
        master_machine_type='n1-standard-4',
        num_master_nodes=1,
        node_pools=(
            NodePool(
                name='gpu-workers',
                machine_type='n1-standard-4',
                accelerator='nvidia-tesla-k80',
                accelerator_count_per_node=1,
                min_nodes=0,
                num_nodes=1,
                max_nodes=10,
                preemptible=True,
            ),
            NodePool(
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
    ),
)

if __name__ == '__main__':
    print(PACKAGE_ROOT_PATH)
