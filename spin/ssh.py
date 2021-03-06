"""This module contains utilities for working with SSH on a local machine."""
import abc
import os
import re
from pathlib import Path
from typing import Text, Optional, Union, List

from spin import utils


def add_line_if_does_not_exist(filename: Union[Text, Path], line: Text):
    """Add the given line to the file unless it's already in the file."""
    if isinstance(filename, Path):
        filename = str(filename)

    with open(filename, 'a+') as f:
        lines = f.readlines()
        if line in lines:
            return
        else:
            f.writelines([line + '\n'])
    return


class KnownHostsModifier:
    def __init__(self, known_hosts_file='~/.ssh/known_hosts'):
        self.known_hosts_file = utils.resolve_path(known_hosts_file)

    def add_known_host(self, line: Text):
        add_line_if_does_not_exist(self.known_hosts_file, line)

    def _get_lines(self) -> List[Text]:
        with open(str(self.known_hosts_file), 'r') as f:
            lines = f.readlines()
        return lines

    def _write_lines(self, lines: List[Text]):
        with open(str(self.known_hosts_file), 'w') as f:
            f.writelines(lines)

    def remove_line(self, line: Text):
        lines = self._get_lines()

        # last line might not end in newline
        if not lines[-1].endswith('\n'):
            lines[-1] += '\n'

        if not line.endswith('\n'):
            line += '\n'
        if line in lines:
            lines.remove(line)

        self._write_lines(lines)

    def remove_all_lines_for_hostname(self, host_name: Text, port: Optional[int] = None):
        lines = self._get_lines()
        host_str = host_name if port is None else f'[{host_name}]:{port}'
        out_lines = [line for line in lines if not line.startswith(host_str)]
        self._write_lines(out_lines)


class FileBlockModifier:
    def __init__(
            self,
            block_start_str=r'######### begin added by spin #########',
            block_end_str=r'########## end added by spin ##########',
            include_leading_newline=True,
    ):
        self.block_start_str = block_start_str
        self.block_end_str = block_end_str
        self.include_leading_newline = include_leading_newline

    def modify(self, filename: Text, new_block: Text, do_replace_old_block=True):
        """if there is a block in the file designated by self.block_start_str and self.block_end_str,
        replace it with the new one.  if there is no such block, put a new one at the end of the file"""
        with open(filename, 'r') as f:
            data = f.read()

        if do_replace_old_block:
            splits = re.split(
                '{}.*{}'.format(self.block_start_str, self.block_end_str),
                data,
                maxsplit=2,
                flags=re.MULTILINE | re.DOTALL,
            )
        else:
            splits = [data]

        new_block_full = []
        if self.include_leading_newline and splits[0][-2:] != '\n\n':
            new_block_full += ['\n']
        new_block_full += [self.block_start_str, '\n']
        new_block_full += [new_block]
        if new_block[-1] != '\n':
            new_block_full += ['\n']
        new_block_full += [self.block_end_str]
        if len(splits) > 1:
            if splits[1][0] != '\n':
                new_block_full += ['\n']
        else:
            new_block_full += ['\n']

        out = ''.join([splits[0]] + new_block_full + splits[1:])

        open(filename, 'w').write(out)

        return


class SshConfigModifier:
    def __init__(
            self,
            config_filename=os.path.expanduser('~/.ssh/config'),
            error_if_config_does_not_exist=False,
            verbose=True
    ):
        self.config_path = Path(config_filename)
        self.error_if_config_does_not_exist = error_if_config_does_not_exist

        if not self.config_path.exists() and self.error_if_config_does_not_exist:
            raise IOError(f'SSH config file, {str(self.config_path)} does not exist.')

        self.file_modifier = FileBlockModifier()
        self.verbose = verbose

    @classmethod
    def _add_to_hosts_dict(cls, d, key, value):
        if value is None:
            return

        if value == True:
            value = 'yes'
        elif value == False:
            value = 'no'

        d[utils.snake_2_camel(key, do_cap_first=True)] = value

    def add_host_entry(
            self,
            host_tag: Text,
            host_name: Optional[Text] = None,
            user: Optional[Text] = None,
            port: Optional[int] = 22,
            identity_file: Optional[Text] = None,  # e.g.: identity_file='~/.ssh/id_rsa'
            add_keys_to_agent: Optional[bool] = True,
            forward_agent: Optional[bool] = True,
            do_replace_existing_spin_hosts_entry=True,
    ):
        """Add a host entry to the ssh config file.
        In general, if you set a option to None its corresponding line will not be included in the final config file."""

        if not self.config_path.exists():
            if self.error_if_config_does_not_exist:
                raise IOError(f'SSH config file, {str(self.config_path)} does not exist.')
            else:
                self.config_path.touch(mode=0o644)

        keys = (
            'host_name',
            'user',
            'port',
            'identity_file',
            'add_keys_to_agent',
            'forward_agent',
        )

        l = locals()
        hosts_dict = {}
        for key in keys:
            self._add_to_hosts_dict(hosts_dict, key, l[key])

        new_hosts_entry_str = f'Host {host_tag}\n'
        new_hosts_entry_str += utils.format_dict(hosts_dict)

        if self.verbose:
            import logging
            logging.info(f'Adding new block of code to file {self.config_path}')
            logging.info(f'{new_hosts_entry_str}')

        self.file_modifier.modify(
            str(self.config_path),
            new_hosts_entry_str,
            do_replace_old_block=do_replace_existing_spin_hosts_entry
        )

        return new_hosts_entry_str

    def remove(self, name: Text):
        from sshconf import read_ssh_config
        conf = read_ssh_config(self.config_path)
        conf.remove(name)
        conf.write(self.config_path)


class SshKeyCreator(utils.ShellRunnerMixin):
    def __init__(
            self,
            private_key_filename='~/.ssh/id_rsa',
            comment='',
            ssh_config_file='~/.ssh/config',
            verbose=True,
    ):
        """

        Args:
            private_key_filename:
            comment: Text
                Probably your email address.
            ssh_config_file:
            verbose:
        """
        super().__init__(verbose)
        self.private_key_path = Path(private_key_filename).expanduser()
        self.comment = comment
        self.ssh_config_modifier = SshConfigModifier(
            Path(ssh_config_file).expanduser(),
            error_if_config_does_not_exist=False,
            verbose=verbose,
        )

    @classmethod
    def get_pub_from_private(cls, private_key_path: Path):
        return Path(str(private_key_path) + '.pub')

    @classmethod
    def get_private_from_pub(cls, public_key_path: Path):
        if Path(public_key_path).suffix != '.pub':
            raise ValueError(f"Expected public key filename to end in .pub.  Got: {str(public_key_path)}.")
        return Path(str(public_key_path[:-4]))

    def create(
            self,
            do_error_if_exists=True,
            do_add_ssh_config_entry=False,
    ):
        # https://unix.stackexchange.com/questions/69314/automated-ssh-keygen-without-passphrase-how
        # correct permissions: https://gist.github.com/grenade/6318301
        # generate with email: https://help.github.com/en/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent
        # TODO: this is osx, do linux

        public_key_path = self.get_pub_from_private(self.private_key_path)
        if self.private_key_path.exists():
            if do_error_if_exists:
                raise IOError(f"File {str(self.private_key_path)} already exists.")
            else:
                if not public_key_path.exists():
                    raise IOError(
                        f"File {str(self.private_key_path)} already exists "
                        f"but matching public key, {str(public_key_path)} is missing.")
                else:
                    # TODO: Handle Config
                    return

        if public_key_path.exists() and do_error_if_exists:
            raise IOError(f"File {str(public_key_path)} already exists.")

        # create key
        command = f'ssh-keygen -t rsa -b 4096 -f {self.private_key_path} -q -N ""'
        if self.comment:
            command += f' -C {self.comment}'
        self._run(command)
        os.chmod(self.private_key_path, 0o600)

        # add key
        self._run('ssh-agent -s')

        self.verbose = False
        exitcode, stdout, stderr = self._run(f'ssh-add -K {str(self.private_key_path)}')
        self.verbose = True
        if exitcode:
            self._run(f'ssh-add {str(self.private_key_path)}')

        if do_add_ssh_config_entry:
            self.ssh_config_modifier.add_host_entry(
                host_tag='*',
                user=None,
                port=None,
                identity_file=str(self.private_key_path),
                add_keys_to_agent=True,
                forward_agent=True,
                do_replace_existing_spin_hosts_entry=False,
            )


class SshKey(utils.DictBouncer, abc.ABC):
    @abc.abstractmethod
    def read_public(self):
        pass

    @abc.abstractmethod
    def read_private(self):
        pass

    def get_known_hosts_line(self, ip: Text, port: int):
        # cut out the hostname or email address comment
        key = ' '.join(self.read_public().split(' ')[:2])

        if port == 22:
            return f'{ip} {key}'
        else:
            return f'[{ip}]:{port} {key}'


class SshKeyOnDisk(SshKey):
    PUB_SUFFIX = '.pub'

    def __init__(self, private_key_file: Text):
        super().__init__()
        self.private_key_path = Path(private_key_file).expanduser().resolve()
        self.public_key_path = self.get_public_from_private(self.private_key_path)

    @classmethod
    def get_public_from_private(cls, private_key_path: Path):
        return Path(str(private_key_path) + cls.PUB_SUFFIX)

    @classmethod
    def get_private_from_public(cls, public_key_path: Path):
        if public_key_path.suffix != cls.PUB_SUFFIX:
            raise ValueError(f"Expected public key filename to end in .pub.  Got: {str(public_key_path)}.")
        return Path(str(public_key_path[:-4]))

    def exists(self, check_private_only=False, check_public_only=False):
        if check_private_only and check_public_only:
            raise ValueError("You should only set one of private_only and public_only but you set both.")

        out = True

        if not check_private_only:
            out &= self.public_key_path.exists()

        if not check_public_only:
            out &= self.private_key_path.exists()

        return out

    def read_public(self):
        if not self.exists(check_public_only=True):
            raise ValueError(f"Key at {str(self.public_key_path)} doesn't exist.")
        return open(str(self.public_key_path), 'r').read()

    def read_private(self):
        if not self.exists(check_private_only=True):
            raise ValueError(f"Key at {str(self.private_key_path)} doesn't exist.")
        return open(str(self.private_key_path), 'r').read()


class SshKeyInMemory(SshKey):
    def __init__(self, public_key_contents: Text, private_key_data: Text):
        super().__init__()
        self._public_key_contents = public_key_contents
        self._private_key_contents = private_key_data

    def read_public(self):
        return self._public_key_contents

    def read_private(self):
        return self._private_key_contents

    @classmethod
    def from_on_disk_key(cls, ssh_key_on_disk: SshKeyOnDisk):
        return cls(ssh_key_on_disk.read_public(), ssh_key_on_disk.read_private())

