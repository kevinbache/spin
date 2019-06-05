import importlib
import os
from pathlib import Path
import sys

from spin.cluster import ClusterDoerInterface


class SpinSettings:
    def __init__(
            self,
            cluster_doer: ClusterDoerInterface,
            # source_repo_doer: SourceControlDoerInterface,
    ):
        self.cluster_doer = cluster_doer
        # self.source_repo_doer = source_repo_doer

    def __eq__(self, o: object) -> bool:
        return type(self) == type(o) and self.__dict__ == o.__dict__

    def __hash__(self) -> int:
        return hash(self.__dict__)


SETTINGS_FILE_ENV_VARIABLE_NAME = 'SPIN_SETTINGS_FILE'
SETTINGS_VARIABLE_NAME = 'SPIN_SETTINGS'


def load_project_settings():
    """Read an environmental variable and load settings from the file it references."""
    if SETTINGS_FILE_ENV_VARIABLE_NAME not in os.environ:
        raise ValueError(f"You haven't set the environmental variable, {SETTINGS_FILE_ENV_VARIABLE_NAME} to point to "
                         f"your project's settings.py file.  You can set it from the terminal with a command like: "
                         f"`$ export {SETTINGS_FILE_ENV_VARIABLE_NAME}=/path/to/your/project/settings.py`")
    settings_filename = os.environ[SETTINGS_FILE_ENV_VARIABLE_NAME]

    if not Path(settings_filename).exists():
        raise ValueError(f"The environmental variable {SETTINGS_FILE_ENV_VARIABLE_NAME} pointed to a settings file, "
                         f"{settings_filename}, which doesn't exist.")

    settings_path = Path(settings_filename)
    sys.path.insert(0, settings_path.parent)
    settings_module = importlib.import_module(settings_path.stem)
    if not hasattr(settings_module, SETTINGS_VARIABLE_NAME):
        raise ValueError(f"Your settings file, {settings_filename}, did not contain a module-level "
                         f"variable named f{SETTINGS_VARIABLE_NAME}")

    spin_settings = getattr(settings_module, SETTINGS_VARIABLE_NAME)
    # if not (hasattr(spin_settings, '_is_spin_settings') and spin_settings._is_spin_settings):
    if not isinstance(spin_settings, SpinSettings):
        raise ValueError(f"The environmental variable {SETTINGS_FILE_ENV_VARIABLE_NAME} "
                         f"pointed to a settings file, {settings_filename}, which contains a module-level variable "
                         f"named {SETTINGS_VARIABLE_NAME} which does not hold a {SpinSettings.__name__} "
                         f"object, but instead an object of type {type(spin_settings)}.")

    sys.path = sys.path[1:]

    return spin_settings
