import os
from pathlib import Path
import pytest

from spin import cluster
from spin import spin_config

SPIN_SETTINGS = spin_config.ProjectConfig(
    cluster=cluster.GkeCluster(
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
    ),
)




if __name__ == '__main__':
    test_load_project_settings()
