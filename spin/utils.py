import shutil

import jinja2
import logging
from pathlib import Path
import re
import shlex
from subprocess import Popen, PIPE
import time
from typing import Text, Dict, Any, Union
import yaml


def snake_2_camel(name, do_cap_first=False):
    words = name.split('_')
    if do_cap_first:
        return ''.join(w.capitalize() for w in words)
    else:
        return words[0] + ''.join(w.capitalize() for w in words[1:])


def camel_2_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def format_dict(d: Dict, indent_width=4):
    max_keylen = max(len(k) for k in d.keys())
    s = ''
    indent = ' ' * indent_width
    for k, v in d.items():
        s += f'{indent}{k:<{max_keylen+2}}{v}\n'
    return s


def get_exitcode_stdout_stderr(cmd, shell=False):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE, shell=shell)
    out, err = proc.communicate()
    exitcode = proc.returncode

    return exitcode, out.decode('utf-8'), err.decode('utf-8')


def ensure_cmdline_program_exists(program_name: Text):
    out = shutil.which(program_name)
    if out is None:
        raise IOError(f"The command line utility, {program_name}, does not exist on your system.")


class ShellRunnerMixin:
    """Can run commands from the command line."""
    EMPTY_RUN_RETURN_VALUE = (0, '', '')

    def __init__(self, verbose=True):
        self.verbose = verbose

    def _run(self, command: Text, error_on_nonzero_exit=True, shell=False):
        if self.verbose:
            logging.info(f'Running shell command: {command}')

        exitcode, stdout, stderr = get_exitcode_stdout_stderr(command, shell)

        if error_on_nonzero_exit and exitcode:
            raise ValueError(f"Got nonzero exit code {exitcode} from command `{command}`.  "
                             f"Stdout: {stdout}.  "
                             f"Stderr: {stderr}.")

        if self.verbose:
            logging.info(f'exitcode: {exitcode}')
            logging.info(f'stdout: {stdout}')
            stderr = stderr.strip()
            if stderr:
                logging.error(f'stderr: {stderr}')

        return exitcode, stdout, stderr


class DictBouncer:
    """This object can bounce itself down to and back up from a dict."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __eq__(self, o: object) -> bool:
        return type(self) == type(o) and self.__dict__ == o.__dict__

    def __hash__(self) -> int:
        return hash(self.__dict__)

    @classmethod
    def _to_dict_inner(cls, element: Any):
        if hasattr(element, 'to_dict'):
            return element.to_dict()
        if isinstance(element, list):
            return [cls._to_dict_inner(e) for e in element]
        elif isinstance(element, tuple):
            return (cls._to_dict_inner(e) for e in element)
        elif isinstance(element, dict):
            return {k: cls._to_dict_inner(v) for k, v in element.items()}
        else:
            return element

    def to_dict(self):
        return self._to_dict_inner(self.__dict__)

    @classmethod
    def from_dict(cls, d: Dict):
        return cls(**d) if d else None

    def __repr__(self):
        kv_str = ', '.join([f'{k}={v}' for k, v in self.to_dict().items()])
        return f'{self.__class__.__name__}({kv_str})'

    def __str__(self):
        return self.__repr__()


class YamlBouncer(DictBouncer):
    """This object can bounce itself down to and back up from a YAML file."""
    def to_yaml(self, filename: Text):
        with open(filename, 'w') as f:
            return yaml.dump(self.to_dict(), f, Dumper=yaml.SafeDumper)

    @classmethod
    def from_yaml(cls, filename: Text):
        with open(filename, 'r') as f:
            return cls.from_dict(yaml.load(f, Loader=yaml.SafeLoader))


def confirm_prompt(prompt_str: Text):
    while True:
        input_str = input(f'{prompt_str} ([y]es/[n]o): ').lower().strip()
        if input_str[:1] == 'y':
            return True
        elif input_str[:1] == 'n':
            return False
        else:
            print('Unrecognized input')


class Timer:
    def __init__(self, name: Text):
        self.name = name

    def __enter__(self):
        self.t = time.time()
        print(f"Starting timer {self.name} at time {self.t}.", end="")

    def __exit__(self, *args):
        print(f"Took {time.time() - self.t}")


def render_template(template_fullfile: Text, context_dict: Dict):
    """Render a jinja template."""
    p = Path(template_fullfile)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(p.parent))
    ).get_template(str(p.name)).render(context_dict)


def file_exists(filename_or_path: Union[Text, Path]):
    filename_or_path = resolve_path(filename_or_path)
    return filename_or_path.exists() and filename_or_path.is_file()


def dir_exists(filename_or_path: Union[Text, Path]):
    filename_or_path = resolve_path(filename_or_path)
    return filename_or_path.exists() and filename_or_path.is_dir()


def resolve_path(path: Union[Text, Path]) -> Path:
    return Path(path).expanduser().resolve()


# if __name__ == '__main__':
#     # if confirm_prompt('Do you want to continue?'):
#     #     print("Continued!")
#     # else:
#     #     print("Stopped!")
#
#     render_template(settings.TEMPLATES_DIR)
