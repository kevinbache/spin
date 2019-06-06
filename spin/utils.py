import logging
import shlex
from subprocess import Popen, PIPE
from typing import Text, Dict, Any, Iterable

import yaml


def snake_2_camel(name, do_cap_first=False):
    words = name.split('_')
    if do_cap_first:
        return ''.join(w.capitalize() for w in words)
    else:
        return words[0] + ''.join(w.capitalize() for w in words[1:])


def format_dict(d: Dict, indent_width=4):
    max_keylen = max(len(k) for k in d.keys())
    s = ''
    indent = ' ' * indent_width
    for k, v in d.items():
        s += f'{indent}{k:<{max_keylen+2}}{v}\n'
    return s


def get_exitcode_stdout_stderr(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    exitcode = proc.returncode

    return exitcode, out.decode('utf-8'), err.decode('utf-8')


class CommandLineInterfacerMixin:
    """Can run commands from the command line."""
    def __init__(self, verbose=True):
        self.verbose = verbose

    def _run(self, command: Text):
        if self.verbose:
            logging.info(f'Running shell command: {command}')

        exitcode, stdout, stderr = get_exitcode_stdout_stderr(command)

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
