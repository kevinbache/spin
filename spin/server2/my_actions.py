from pathlib import Path
from typing import Text, Optional

from spin import ssh
from spin.server2 import tryout_server
from spin.server2.tryout_server import SingleValueAction


class SendPublicKey(SingleValueAction):
    SERVERSIDE_AUTHORIZED_KEYS_LOCATION = str(Path('~/.ssh/authorized_keys').expanduser())

    def __init__(self, local_public_key_filename: Text):
        super().__init__(route='send_public_key')

        p = Path(local_public_key_filename).expanduser().resolve()
        if not p.exists() or not p.is_file():
            raise ValueError(f"File {local_public_key_filename} does not exist or is not a file.")
        self.public_key_path = p

    def local_value(self) -> Text:
        return self.public_key_path.read_text()

    def remote_value(self, value: Text) -> Optional[Text]:
        public_key_contents = value

        authorized_keys_path = Path(self.SERVERSIDE_AUTHORIZED_KEYS_LOCATION)
        if not authorized_keys_path.exists():
            authorized_keys_path.touch(mode=0o644)

        ssh.add_line_if_does_not_exist(self.SERVERSIDE_AUTHORIZED_KEYS_LOCATION, public_key_contents)

        return 'success'


def get_server() -> tryout_server.Server:
    return tryout_server.Server(host='localhost', port=5000, actions=[
        SendPublicKey('~/.ssh/id_rsa.pub'),
    ])


def zero_counter(number_str: Text):
    return number_str.count('0')


if __name__ == '__main__':
    s = get_server()
    s.serve()
