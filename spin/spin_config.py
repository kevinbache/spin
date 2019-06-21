"""This module contains utilities for saving and loading system-wide and project-wide settings."""
import importlib
from pathlib import Path
import sys
from typing import Dict, Text, Optional, List

from spin import settings
from spin.cluster import Cluster
from spin.utils import DictBouncer, YamlBouncer


class SpinRcProject(DictBouncer):
    _DEFAULT_FILENAME = 'config.py'

    @classmethod
    def get_config_location_from_project_directory(cls, project_directory: Text):
        project_directory_path = Path(project_directory)
        project_slug = project_directory_path.stem
        return str(project_directory_path / project_slug / cls._DEFAULT_FILENAME)

    def __init__(
            self,
            project_dir: Text,
            name: Optional[Text] = None,
            project_config_file: Optional[Text] = None,
    ):
        super().__init__()

        project_path = Path(project_dir)
        self.project_dir = project_dir

        if name is None:
            name = str(project_path.stem)
        self.name = name

        if project_config_file is None:
            project_config_file = self.get_config_location_from_project_directory(project_path)
        self.project_config_file = project_config_file

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
    DEFAULT_LOCATION_STR = str(DEFAULT_LOCATION_PATH)

    def __init__(
            self,
            user: SpinRcUser,
            projects: List[SpinRcProject],
            current_project: Text=None,
    ):
        self.user = user
        self.projects = projects
        self.current_project = current_project

    def add_project(self, project: SpinRcProject, set_current=False):
        self.projects.append(project)
        if set_current:
            self.set_current_project(project.name)

    def set_user(self, user: SpinRcUser):
        self.user = user

    def set_current_project(self, project_name):
        if project_name not in [p.name for p in self.projects]:
            raise ValueError(f"There is no project named {project_name}")

        self.current_project = project_name

    def get_current_project(self) -> Optional[SpinRcProject]:
        if self.current_project is None:
            return None

        for project in self.projects:
            if project.name == self.current_project:
                return project

        raise ValueError(f"Your .spinrc file's current_project={self.current_project} "
                         f"but there is no project with that name.")

    @classmethod
    def from_dict(cls, d: Dict):
        user = SpinRcUser.from_dict(d.get('user', {}))
        del d['user']
        projects = [SpinRcProject.from_dict(p) for p in d.get('projects', [])]
        del d['projects']
        return cls(user, projects, **d)

    def save(self, filename: Text = settings.SPIN_RC_PATH_STR):
        self.to_yaml(filename)

    @classmethod
    def load(cls, filename: Text = settings.SPIN_RC_PATH_STR) -> 'SpinRc':
        d = cls.from_yaml(filename)
        if d is None:
            raise ValueError(f"Got empty spin rc file at location {filename}")
        return d

    @classmethod
    def load_and_set_current_project_and_save(cls, project_name: Text):
        rc = cls.load()
        rc.set_current_project(project_name)
        rc.save()

    @classmethod
    def load_and_get_current_project(cls) -> Optional[SpinRcProject]:
        rc = cls.load()
        return rc.get_current_project()


class ProjectConfig:
    def __init__(
            self,
            name: Text,
            cluster: Cluster,
    ):
        self.name = name
        self.cluster = cluster

    def __eq__(self, o: object) -> bool:
        return type(self) == type(o) and self.__dict__ == o.__dict__

    def __hash__(self) -> int:
        return hash(self.__dict__)


PROJECT_CONFIG_VARIABLE_NAME = 'PROJECT_CONFIG'


def load_project_config_from_config_filename(config_filename):
    config_file_path = Path(config_filename)

    if not config_file_path.exists():
        raise ValueError(f"Tried to load project config from {config_filename} but it doesn't exist.")

    sys.path.insert(0, config_file_path.parent)
    import_str = f'{config_file_path.parent.stem}.{config_file_path.stem}'
    config_module = importlib.import_module(import_str)
    if not hasattr(config_module, PROJECT_CONFIG_VARIABLE_NAME):
        raise ValueError(f"Your project config file, {config_filename}, did not contain a module-level "
                         f"variable named f{PROJECT_CONFIG_VARIABLE_NAME}")

    project_config = getattr(config_module, PROJECT_CONFIG_VARIABLE_NAME)
    if not isinstance(project_config, ProjectConfig):
        raise ValueError(f"Tried to load a project config file, {config_filename}, which contains a "
                         f"module-level variable named {PROJECT_CONFIG_VARIABLE_NAME} "
                         f"which does not hold a {ProjectConfig.__name__} "
                         f"object, but instead an object of type {type(project_config)}.")

    sys.path = sys.path[1:]

    return project_config


def load_project_config_from_spinrc(spinrc_filename: Text = SpinRc.DEFAULT_LOCATION_STR):
    rc = SpinRc.load(spinrc_filename)
    project = rc.get_current_project()
    if project is None:
        raise ValueError(f"There's no current project in your spinrc located at {spinrc_filename}")
    return load_project_config_from_config_filename(project.project_config_file)


if __name__ == '__main__':
    config = load_project_config_from_spinrc()


