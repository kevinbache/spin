import abc
from pathlib import Path
from typing import Text, Dict, Callable

import requests

from flask import Flask
# from flask import request

app = Flask(__name__)


class Server:
    def __init__(self, host: Text, port: int):
        self.host = host
        self.port = port
        self.protocol = 'https'

    def get_url(self, path: Text):
        return f'{self.protocol}://{self.host}:{self.port}/{path}'

    @abc.abstractmethod
    def send(self, url_path: Text, d: Dict) -> requests.Response:
        return requests.post(self.get_url(url_path), json=d)

TextDict = Dict[Text, Text]

class PostDictAction(abc.ABC):
    def __init__(self, server: Server, route_name: Text, handle_dict_fn: Callable[[TextDict], requests.Response]):
        self.route_name = route_name
        self.server = server
        self._handle_dict_fn = handle_dict_fn

        # register with flask
        self.handle = app.route(self.route_name, methods=['POST'])(self._handle_dict_fn)

    def send(self, d: Dict):
        return self.server.send(self.route_name, d)

    # def handle(self, sent_dict: Dict[Text, Text]):
    #     return self._handle_dict(sent_dict)

    # @abc.abstractmethod
    # def _handle_dict(self, sent_dict: Dict[Text, Text]):
    #     pass


class SingleFieldPostDictAction(PostDictAction):
    def __init__(self, server: Server, route_name: Text, request_field_name: Text):
        super().__init__(server, route_name)
        self.request_field_name = request_field_name

    def _handle_dict(self, sent_dict: Dict[Text, Text]):
        if self.request_field_name not in sent_dict:
            raise ValueError(f"Couldn't find field {self.request_field_name} in your request which included fields: "
                             f"{sent_dict.keys()}")
        return self._handle_field(sent_dict[self.request_field_name])

    @abc.abstractmethod
    def _handle_field(self, sent_value: Text):
        pass

    def send_value(self, value_to_send: Text):
        return self.send({self.request_field_name: value_to_send})


class AddAuthorizedKeyAction:



class DevboxServerStub:
    def __init__(self, host: Text, port: int):
        self.host = host
        self.port = port
        self.protocol = 'https'

    def get_url(self, path: Text):
        return f'{self.protocol}://{self.host}:{self.port}/{path}'

    add_public_key_route = 'add_public_key'
    add_public_key_field = 'public_key'

    def send_public_key(self, filename):
        p = Path(filename)
        if not p.exists() and p.is_file():
            raise ValueError(f"Public key file, {filename}, doesn't exist or isn't a file.")

        data = {
            self.add_public_key_field: 'XXXXXXXXX YYYYYYYYYYY ZZZZZZZZZZZ'
        }
        response = requests.post(self.get_url(''), json=data)

    @app.route(add_public_key_route, methods=['POST'])
    def add_authorized_host(self):
        request_data = request.get_json(force=True)


if __name__ == '__main__':
    data = {
        'public_key': 'XXXXXXXXX YYYYYYYYYYY ZZZZZZZZZZZ'
    }
    response = requests.post('http://localhost:5000/add_auth_key', json=data)
    print(f'response from server: {response.text}')
    print(f'response.json():      {response.json()}')
