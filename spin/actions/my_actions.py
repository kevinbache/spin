from pathlib import Path
from typing import Text, Optional

from spin import actions


def add_line_if_does_not_exist(filename: Text, line: Text):
    """Add the given line to the file unless it's already in the file."""
    with open(filename, 'a+') as f:
        lines = f.readlines()
        if line in lines:
            return
        else:
            f.writelines([line])
    return


class AddAuthorizedKey(actions.SingleValueAction):
    """Add a local public key to a remote authorized_keys file."""
    def __init__(
            self,
            local_public_key_filename: Text,
            remote_authorized_keys_location=str(Path('~/.ssh/authorized_keys').expanduser()),
    ):
        self.local_public_key_path = Path(local_public_key_filename).expanduser().resolve()
        self.remote_authorized_keys_location = remote_authorized_keys_location

        super().__init__(route='send_public_key')

    def _local_single_value(self) -> Text:
        return self.local_public_key_path.read_text()

    def _remote_single_value(self, value: Text) -> Optional[Text]:
        public_key_contents = value

        authorized_keys_path = Path(self.remote_authorized_keys_location)

        if not authorized_keys_path.parent.exists():
            authorized_keys_path.parent.mkdir(mode=0o755, parents=True)

        if not authorized_keys_path.exists():
            authorized_keys_path.touch(mode=0o644)

        add_line_if_does_not_exist(self.remote_authorized_keys_location, public_key_contents)

        return 'success'

    def _verify_on_client(self):
        if not self.local_public_key_path.exists():
            raise ValueError(f"Local public key path, {self.local_public_key_path} doesn't exist.")

        if not self.local_public_key_path.is_file():
            raise ValueError(f"Local public key path, {self.local_public_key_path} is not a file.")


class DevBoxServer(actions.Server):
    def _set_actions(self):
        out = {}

        out['send_public_key'] = AddAuthorizedKey('~/.ssh/id_rsa.pub')
        self.send_public_key = out['send_public_key']

        return out


if __name__ == '__main__':
    s = DevBoxServer(as_client=False, host='localhost', port=5000)
    s.debug_serve()
