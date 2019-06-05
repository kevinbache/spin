import os
from pathlib import Path
from typing import Text

from spin import ssh
import tempfile


def test_add_config():
    t = tempfile.NamedTemporaryFile()
    m = ssh.SshConfigModifier(t.name)

    existing_host = """Host existing_host
    HostName 127.0.0.1
    User myUser
    IdentityFile ~/.ssh/id_rsa
    ForwardAgent yes
"""
    with open(t.name, 'w') as f:
        f.write(existing_host)

    m.add_host_entry(
        host_tag='host_tag',
        host_name='localhost',
        user=None,
        identity_file='~/.ssh/id_rsa'
    )

    expected_output = '''Host existing_host
    HostName 127.0.0.1
    User myUser
    IdentityFile ~/.ssh/id_rsa
    ForwardAgent yes

######### begin added by spin #########
Host host_tag
    HostName        localhost
    Port            22
    IdentityFile    ~/.ssh/id_rsa
    AddKeysToAgent  yes
    ForwardAgent    yes
########## end added by spin ##########
'''
    out = open(t.name, 'r').read()
    assert expected_output == out

    # OVERWRITE OLD SPIN HOSTS ENTRY
    m.add_host_entry(
        host_tag='host_tag',
        host_name='127.0.0.1',
        user='myuser',
        add_keys_to_agent=False,
        identity_file='~/.ssh/id_rsa',
        do_replace_existing_spin_hosts_entry=True,
    )

    expected_output = '''Host existing_host
    HostName 127.0.0.1
    User myUser
    IdentityFile ~/.ssh/id_rsa
    ForwardAgent yes

######### begin added by spin #########
Host host_tag
    HostName        127.0.0.1
    User            myuser
    Port            22
    IdentityFile    ~/.ssh/id_rsa
    AddKeysToAgent  no
    ForwardAgent    yes
########## end added by spin ##########
'''
    out = open(t.name, 'r').read()
    assert expected_output == out

    # DO NOT OVERWRITE OLD SPIN HOSTS ENTRY
    m.add_host_entry(
        host_tag='host_tag',
        host_name='127.0.0.1',
        user='myuser',
        add_keys_to_agent=False,
        identity_file='~/.ssh/id_rsa',
        do_replace_existing_spin_hosts_entry=False,
    )

    expected_output = '''Host existing_host
    HostName 127.0.0.1
    User myUser
    IdentityFile ~/.ssh/id_rsa
    ForwardAgent yes

######### begin added by spin #########
Host host_tag
    HostName        127.0.0.1
    User            myuser
    Port            22
    IdentityFile    ~/.ssh/id_rsa
    AddKeysToAgent  no
    ForwardAgent    yes
########## end added by spin ##########

######### begin added by spin #########
Host host_tag
    HostName        127.0.0.1
    User            myuser
    Port            22
    IdentityFile    ~/.ssh/id_rsa
    AddKeysToAgent  no
    ForwardAgent    yes
########## end added by spin ##########
'''
    out = open(t.name, 'r').read()
    assert expected_output == out


def _get_file_permission(filename: Text):
    return oct(os.stat(filename).st_mode & 0o777)


def test_new_identity():
    with tempfile.TemporaryDirectory() as tdir:
        tdir = Path(tdir)
        print(tdir)

        private_file = str(tdir / 'my_ssh_key')
        config_file = str(tdir / 'config')

        assert not Path(private_file).exists()
        assert not Path(config_file).exists()

        comment = 'my.email@gmail.com'
        k = ssh.SshKeyCreater(
            private_key_filename=private_file,
            comment=comment,
            ssh_config_file=config_file,
        )

        assert not Path(private_file).exists()
        assert not Path(config_file).exists()

        #######################
        # create a first time #
        #######################
        k.create(do_error_if_exists=True, do_add_ssh_config_entry=True)

        public_file = private_file + '.pub'
        assert Path(private_file).exists()
        assert _get_file_permission(private_file) == oct(0o600)
        assert Path(public_file).exists()
        assert _get_file_permission(public_file) == oct(0o644)
        assert Path(config_file).exists()
        assert _get_file_permission(config_file) == oct(0o644)

        pub_contents = open(public_file, 'r').read()
        assert comment in pub_contents

        host_entry = f"""Host *
    IdentityFile    {private_file}
    AddKeysToAgent  yes
    ForwardAgent    yes"""

        private_str = open(private_file, 'r').read()
        public_str = open(public_file, 'r').read()
        config_str = open(config_file, 'r').read()
        assert host_entry in config_str

        ##############################################
        # create again, everything remains unchanged #
        ##############################################
        k.create(do_error_if_exists=False, do_add_ssh_config_entry=True)

        assert Path(private_file).exists()
        assert _get_file_permission(private_file) == oct(0o600)
        assert Path(public_file).exists()
        assert _get_file_permission(public_file) == oct(0o644)
        assert Path(config_file).exists()
        assert _get_file_permission(config_file) == oct(0o644)

        assert private_str == open(private_file, 'r').read()
        assert public_str == open(public_file, 'r').read()
        assert config_str == open(config_file, 'r').read()


if __name__ == '__main__':
    test_add_config()
    test_new_identity()
