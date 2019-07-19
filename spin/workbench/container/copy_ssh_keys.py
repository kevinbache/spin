"""This file contains routines for copying ssh keys from a mounted kubernetes secrets directory into the appropriate
spots on a workbench container.  It is meant to be run when the container boots up.
"""
import argparse
import glob
from pathlib import Path
import os
import shlex
import shutil
from subprocess import Popen, PIPE
from typing import Text, Tuple, List, Union


def resolve_path(path: Union[Text, Path]) -> Path:
    return Path(path).expanduser().resolve()


def shell_run(cmd, shell=True):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE, shell=shell)
    stdout, stderr = proc.communicate()
    stdout = stdout.decode('utf-8')
    stderr = stderr.decode('utf-8')
    exitcode = proc.returncode

    if exitcode != 0:
        raise ValueError(f"Error running command {cmd}.  Stdout: {stdout}.  Stderr: {stderr}.")

    return exitcode, stdout, stderr


def add_line_if_does_not_exist(filename: Text, line: Text):
    """Add the given line to the file unless it's already in the file."""
    with open(filename, 'a+') as f:
        lines = f.readlines()
        if line in lines:
            return
        else:
            f.writelines([line])
    return


def find_key_pairs(dir_to_search: Text) -> List[Tuple[Text, Text]]:
    """get a list of (pub, private) key pair filenames within the given directory"""
    path_to_search = Path(dir_to_search)
    pub_files = glob.glob(str(path_to_search / '*.pub'))
    all_files = glob.glob(str(path_to_search / '*'))
    key_pairs = []
    for pub_file in pub_files:
        private_file = os.path.splitext(pub_file)[0]
        if private_file not in all_files:
            raise ValueError(f"Couldn't find corresponding private key for public key {pub_file}."
                             f"all_files: {str(all_files)}")
        key_pairs.append((pub_file, private_file))
    return key_pairs


def copy_and_add_key_pairs(key_pairs: List[Tuple[Text, Text]], target_dir: Text, do_add=True):
    print('\nStarting copy_and_add_key_pairs')
    for public_key, private_key in key_pairs:
        print(f'copy_and_add_key_pairs is copying {public_key} into {target_dir}')
        shutil.copy2(public_key, target_dir)
        target_public_key = str(Path(target_dir) / Path(public_key).name)
        print(f'chmodding target_public_key {target_public_key} to 644')
        os.chmod(target_public_key, mode=0o644)

        print(f'copy_and_add_key_pairs is copying {private_key} into {target_dir}')
        shutil.copy2(private_key, target_dir)
        target_private_key = str(Path(target_dir) / Path(private_key).name)
        print(f'chmodding target_private_key {target_private_key} to 600')
        os.chmod(target_private_key, mode=0o600)

        if do_add:
            cmd = f'eval "$(ssh-agent -s)" && ssh-add -K {target_private_key}'
            print(f"Running ssh-add command: {cmd}")
            shell_run(cmd, shell=True)


def copy_ssh_keys(
        ssh_server_keys_mountpoint='/secrets/ssh_server_keys',
        user_keys_mountpoint='/secrets/user_keys',
        user_login_public_keys_mountpoint='/secrets/user_login_public_keys',
        authorized_keys_file='~/.ssh/authorized_keys',
        ssh_dir='~/.ssh/'
):
    """Copy ssh keys from a secrets directory to the appropriate places on a container to enable
        1) running an SSH server (keys in server_keys_subdir)
        2) the user to pull from private repos (keys in user_keys_subdir)
        3) the user to SSH into that server (keys in user_login_key_subdir)

    Args:
        ssh_server_keys_mountpoint:
        user_keys_mountpoint:
        user_login_public_keys_mountpoint:
        authorized_keys_file:
        ssh_dir:

    """
    ##################################################
    # add ssh_server_keys to /etc/ssh
    print("\nAdding ssh_server_keys to /etc/ssh")
    server_key_pairs = find_key_pairs(ssh_server_keys_mountpoint)
    copy_and_add_key_pairs(server_key_pairs, '/etc/ssh/', do_add=False)

    shell_run('ls -la /etc/ssh')

    ##################################################
    # add users's private/public keys with ssh-add
    print("\nAdding users's private/public keys with ssh-add")
    ssh_dir_path = Path(ssh_dir).expanduser().resolve()
    if not ssh_dir_path.exists():
        ssh_dir_path.mkdir(parents=True, mode=0o700)
    elif not ssh_dir_path.is_dir():
        raise ValueError(f"ssh directory, {str(ssh_dir_path)}, exists but isn't a directory.")
    ssh_dir = str(ssh_dir_path)
    user_key_pairs = find_key_pairs(user_keys_mountpoint)
    copy_and_add_key_pairs(user_key_pairs, ssh_dir)

    ##################################################
    # add user's login public key(s) as authorized_keys
    authorized_keys_path = Path(authorized_keys_file).expanduser().resolve()

    # create authorized_keys dir
    authorized_keys_dir_path = authorized_keys_path.parent
    if not authorized_keys_dir_path.exists():
        authorized_keys_dir_path.mkdir(parents=True, mode=0o700)
    elif not authorized_keys_dir_path.is_dir():
        raise ValueError(f"authorized_keys directory, {str(authorized_keys_dir_path)}, exists but isn't a directory.")

    # create authorized_keys file
    if not authorized_keys_path.exists():
        authorized_keys_path.touch(mode=0o644)

    # add public keys to authorized_keys
    pub_files = glob.glob(str(Path(user_login_public_keys_mountpoint) / '*.pub'))
    for pub_file in pub_files:
        pub_key_contents = open(pub_file, 'r').read()
        print(f"\nAdding line {pub_key_contents} to file {str(authorized_keys_path)}")
        add_line_if_does_not_exist(str(authorized_keys_path), pub_key_contents)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--ssh_server_keys_mountpoint", default='/secrets/ssh-server-keys')
    parser.add_argument("--user_keys_mountpoint", default='/secrets/user-keys')
    parser.add_argument("--user_login_public_keys_mountpoint", default='/secrets/user-login-public-keys')
    args = parser.parse_args()

    copy_ssh_keys(**vars(args))
