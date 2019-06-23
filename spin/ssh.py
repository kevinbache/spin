"""This module contains utilities for working with SSH on a local machine."""
import os
import re
from pathlib import Path
from typing import Text, Optional

from spin import utils


def add_line_if_does_not_exist(filename: Text, line: Text):
    """Add the given line to the file unless it's already in the file."""
    with open(filename, 'a') as f:
        lines = f.readlines()
        if line in lines:
            return
        else:
            f.writelines([line])
    return


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


class SshKeyCreater(utils.ShellRunnerMixin):
    def __init__(
            self,
            private_key_filename='~/.ssh/id_rsa',
            comment='',
            ssh_config_file='~/.ssh/config',
            verbose=True,
    ):
        super().__init__(verbose)
        self.private_key_path = Path(private_key_filename).expanduser()
        self.comment = comment
        self.ssh_config_modifier = SshConfigModifier(
            Path(ssh_config_file).expanduser(),
            error_if_config_does_not_exist=False,
            verbose=verbose,
        )

    @classmethod
    def _get_pub_from_private(self, private_key_path: Path):
        return Path(str(private_key_path) + '.pub')

    @classmethod
    def _get_private_from_pub(self, public_key_path: Path):
        if public_key_path.suffix != '.pub':
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

        public_key_path = self._get_pub_from_private(self.private_key_path)
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

        self.verbose = verbose

        self.file_modifier = FileBlockModifier()

    # https://unix.stackexchange.com/questions/69314/automated-ssh-keygen-without-passphrase-how
    '''ssh-keygen -b 2048 -t rsa -f /tmp/sshkey -q -N ""'''
    # correct permissions: https://gist.github.com/grenade/6318301
    # generate with email: https://help.github.com/en/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

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


if __name__ == '__main__':
    # m = SshConfigModifier()
    # print()
    # print(open(m.config_path, 'r').read())
    # m.add_host_entry(
    #     host_tag='host_tag',
    #     host_name='localhost',
    #     user='kevin',
    #     identity_file='~/.ssh/id_rsa',
    #     forward_agent=True,
    #     add_keys_to_agent=None,
    #     do_replace_existing_spin_hosts_entry=True,
    # )
    # print()
    # print(open(m.config_path, 'r').read())

