"""This module contains utilities for saving and loading system-wide and project-wide settings."""
import importlib
import os
from pathlib import Path
import sys
from typing import Dict, Text, Optional, List

from spin import settings
from spin.cluster import Cluster
from spin.utils import DictBouncer, YamlBouncer


class ProjectConfig:
    def __init__(
            self,
            cluster: Cluster,
    ):
        self.cluster = cluster

    def __eq__(self, o: object) -> bool:
        return type(self) == type(o) and self.__dict__ == o.__dict__

    def __hash__(self) -> int:
        return hash(self.__dict__)


SETTINGS_FILE_ENV_VARIABLE_NAME = 'SPIN_SETTINGS_FILE'
SETTINGS_VARIABLE_NAME = 'SPIN_SETTINGS'


# Why have a yaml-formatted .spinrc and a settings.py for project config?
# Project config is more complex.  You want it to be refactorable and you want to be able to use loops.
# .spinrc is simpler and has values which exist outside of any particular project.
#    It doesn't need to be on your python path.
def load_project_config_from_env():
    """Read an environmental variable and load settings from the file it references."""
    if SETTINGS_FILE_ENV_VARIABLE_NAME not in os.environ:
        raise ValueError(f"You haven't set the environmental variable, {SETTINGS_FILE_ENV_VARIABLE_NAME} to point to "
                         f"your project's settings.py file.  You can set it from the terminal with a command like: "
                         f"`$ export {SETTINGS_FILE_ENV_VARIABLE_NAME}=/path/to/your/project/settings.py`")
    settings_filename = os.environ[SETTINGS_FILE_ENV_VARIABLE_NAME]
    return load_project_config_from_settings_filename(settings_filename)


def get_settings_file_from_env():
    if SETTINGS_FILE_ENV_VARIABLE_NAME in os.environ:
        return os.environ[SETTINGS_FILE_ENV_VARIABLE_NAME]
    else:
        return None

# def read_settings_file_from_spinrc():
#


def load_project_config_from_settings_filename(settings_filename):
    settings_path = Path(settings_filename)

    if not settings_path.exists():
        raise ValueError(f"The environmental variable {SETTINGS_FILE_ENV_VARIABLE_NAME} pointed to a settings file, "
                         f"{settings_filename}, which doesn't exist.")

    sys.path.insert(0, settings_path.parent)
    settings_module = importlib.import_module(settings_path.stem)
    if not hasattr(settings_module, SETTINGS_VARIABLE_NAME):
        raise ValueError(f"Your settings file, {settings_filename}, did not contain a module-level "
                         f"variable named f{SETTINGS_VARIABLE_NAME}")

    spin_settings = getattr(settings_module, SETTINGS_VARIABLE_NAME)
    if not isinstance(spin_settings, ProjectConfig):
        raise ValueError(f"The environmental variable {SETTINGS_FILE_ENV_VARIABLE_NAME} "
                         f"pointed to a settings file, {settings_filename}, which contains a module-level variable "
                         f"named {SETTINGS_VARIABLE_NAME} which does not hold a {ProjectConfig.__name__} "
                         f"object, but instead an object of type {type(spin_settings)}.")

    sys.path = sys.path[1:]

    return spin_settings


PROJECT_CONFIG_FILENAME = 'config.py'


class SpinRcProject(DictBouncer):
    DEFAULT_FILENAME = 'config.py'

    @classmethod
    def get_config_location_from_project_directory(cls, project_directory: Text):
        project_directory_path = Path(project_directory)
        project_slug = project_directory_path.stem
        return str(project_directory_path / project_slug / cls.DEFAULT_FILENAME)

    def __init__(
            self,
            project_dir: Text,
            name: Optional[Text] = None,
            project_config_file: Optional[Text] = None,
            is_current=False,
    ):
        super().__init__()

        project_path = Path(project_dir)
        self.project_dir = project_dir

        if name is None:
            name = str(project_path.stem)
        self.name = name

        if project_config_file is None:
            project_config_file = str(project_path / PROJECT_CONFIG_FILENAME)
        self.project_config_file = project_config_file

        self.is_current = is_current

    def set_as_current(self):
        self.is_current = True


class SpinRcUser(DictBouncer):
    def __init__(self, name: Text, email: Text, github_username: Text):
        super().__init__()
        self.name = name
        self.email = email
        self.github_username = github_username


class SpinRc(YamlBouncer):
    DEFAULT_FILENAME = '.spinrc'
    DEFAULT_LOCATION_PATH = Path.home() / DEFAULT_FILENAME

    def __init__(self, user: SpinRcUser, projects: List[SpinRcProject]):
        super().__init__()
        self.user = user
        self.projects = projects

    def add_project(self, project: SpinRcProject):
        self.projects.append(project)

    def set_user(self, user: SpinRcUser):
        self.user = user

    def set_current_project(self, project_name):
        if project_name not in [p.name for p in self.projects]:
            raise ValueError(f"There is no project named {project_name}")

        for project in self.projects:
            if project.name == project_name:
                project.is_current = True
            else:
                project.is_current = False

    def get_current_project(self) -> Optional[SpinRcProject]:
        for project in self.projects:
            if project.is_current:
                return project

        return None

    @classmethod
    def from_dict(cls, d: Dict):
        user = SpinRcUser.from_dict(d.get('user', {}))
        projects = [SpinRcProject.from_dict(p) for p in d.get('projects', [])]
        return cls(user, projects)

    def save(self, filename: Text = settings.SPIN_RC_PATH_STR):
        self.to_yaml(filename)

    @classmethod
    def load(cls, filename: Text = settings.SPIN_RC_PATH_STR) -> 'SpinRc':
        d = cls.from_yaml(filename)
        if d is None:
            raise ValueError(f"Got empty spin rc file at location {filename}")
        return d

    @classmethod
    def load_set_current_project_save(cls, project_name: Text):
        rc = cls.load()
        rc.set_current_project(project_name)
        rc.save()

    @classmethod
    def load_get_current_project(cls) -> Optional[SpinRcProject]:
        rc = cls.load()
        return rc.get_current_project()
