import os
from pathlib import Path
import pytest

from spin import cluster
from spin import spin_settings

SPIN_SETTINGS = spin_settings.SpinSettings(
    cluster_doer=cluster.GkeClusterDoer(
        cluster_name='my-cluster',
        zone='us-central1-a',
        master_machine_type='n1-standard-4',
        num_master_nodes=1,
        node_pool_configs=(
            cluster.NodePoolConfig(
                name='gpu-workers',
                machine_type='n1-standard-4',
                accelerator='nvidia-tesla-k80',
                accelerator_count_per_node=1,
                min_nodes=0,
                num_nodes=1,
                max_nodes=10,
                preemptible=True,
            ),
            cluster.NodePoolConfig(
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


def test_load_project_settings():
    VAR_NAME = spin_settings.SETTINGS_FILE_ENV_VARIABLE_NAME
    if VAR_NAME in os.environ:
        del os.environ[VAR_NAME]

    # fail without env var
    with pytest.raises(ValueError):
        spin_settings.load_project_settings()

    # work with env var
    os.environ[VAR_NAME] = str(Path(__file__).resolve())
    loaded_settings = spin_settings.load_project_settings()
    assert loaded_settings == SPIN_SETTINGS

    # check that SpinSettings.__eq__ is doing what we think
    loaded_settings.cluster_doer.cluster_name = 'NEW_NAME'
    assert loaded_settings != SPIN_SETTINGS


if __name__ == '__main__':
    test_load_project_settings()
