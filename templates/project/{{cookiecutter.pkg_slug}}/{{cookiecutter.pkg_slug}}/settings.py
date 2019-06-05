from pathlib import Path

from spin.cluster import GkeClusterDoer, NodePoolConfig
from spin.spin_settings import SpinSettings

PACKAGE_ROOT_PATH = Path(__file__).resolve().parent

PROJECT_ROOT_PATH = PACKAGE_ROOT_PATH / '..'
TESTS_PATH = PROJECT_ROOT_PATH / 'test'

SPIN_SETTINGS = SpinSettings(
    cluster_doer=GkeClusterDoer(
        cluster_name='my-cluster',
        zone='us-central1-a',
        master_machine_type='n1-standard-4',
        num_master_nodes=1,
        node_pool_configs=(
            NodePoolConfig(
                name='gpu-workers',
                machine_type='n1-standard-4',
                accelerator='nvidia-tesla-k80',
                accelerator_count_per_node=1,
                min_nodes=0,
                num_nodes=1,
                max_nodes=10,
                preemptible=True,
            ),
            NodePoolConfig(
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
