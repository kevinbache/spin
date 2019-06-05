import logging
import shlex
from subprocess import Popen, PIPE
from typing import Text, Dict


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
