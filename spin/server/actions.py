from pathlib import Path
import requests
from typing import Text, Optional, Any

from spin import utils
from spin.server import server


class AddKnownKeyAction(server.SingleFieldAction, utils.ShellRunnerMixin):
    ROUTE = 'add_known_key'

    def __init__(self, verbose=True):
        super().__init__(self.ROUTE)
        self.verbose = verbose

    def _on_client_value(self, public_key_filename: Text) -> Any:
        p = Path(public_key_filename)
        if not p.exists() or not p.is_file():
            raise ValueError(f"Public key file referenced at {public_key_filename} does not exist or is not a file.")
        return p.read_text()

    def _on_server_value(self, value: Any) -> Optional[requests.Response]:
        print(f'Received value: {value}')
        return None

