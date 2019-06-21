import abc
import enum
from pathlib import Path
from typing import Text, Dict, Callable

import requests
import typing

from flask import Flask
# from flask import request

app = Flask(__name__)


class AddPublicKeyAction():



class DevboxActions(enum.Enum):
    add_public_key = StaticSingleFieldPostDictAction()




class Server:
    def __init__(self, host: Text, port: int):
        self.host = host
        self.port = port
        self.protocol = 'https'

    def get_url(self, path: Text):
        return f'{self.protocol}://{self.host}:{self.port}/{path}'

    @abc.abstractmethod
    def send_from_client(self, url_path: Text, d: Dict) -> requests.Response:
        return requests.post(self.get_url(url_path), json=d)

    @abc.abstractmethod
    def serve(self):
        pass


TextDict = Dict[Text, Text]

# the problem i keep coming up against is that i'd like to be able to create a subclass which overrides certain fields
# without having to retype out the __init__ method
#
# get over it

# # client is local machine.  i want to say:
# response = server.add_public_key(public_key_filename)
# # in fact just
# server.add_public_key(public_key_filename)
# # and have add_public_key's handler automatically check that the response isn't malformed
#
# # this is the task registry
# server.register(add_public_key_action)
#
# server = DevboxServer(host=host, port=port)
# server.add_public_key(public_key_filename)

# under the hood, i want server to be an enum of callables.  each callable's __call__ method needs to
# the problem is how then do you register the server with each action?  if the server is or contains an enum,
# then how does it call set_server on each of its members?  maybe in the server init?

class TestServer(enum.Enum):




    def serve(self):
        pass


class Action:
    def __init__(self, route_name: Text):
        # 1 - create your action
        self.route_name = route_name
        self.server = FailServer()

    def __call__(self, *args, **kwargs):
        self.server.send(self._get_request(*args, **kwargs))

    @abc.abstractmethod
    def get_request_dict(self, d: Dict):
        return requests.Request(json=d)

    def set_server(self, server: Server):
        # 2 - introduce it to its server on the client side
        self.server = server

    def send(self, request: requests.Request):
        # 3 - send a message from the client
        # return self.server.send(self.route_name, d)

    @abc.abstractmethod
    def handle(self, request: requests.Request) -> requests.Response:
        pass


    def handle(self, sent_dict: Dict[Text, Text]):
        # 4 - handle a message on the server
        return self._handle_dict(sent_dict)



class PostDictAction(abc.ABC):
    def __init__(self, route_name: Text):
        # 1 - create your action
        self.route_name = route_name
        self.server = FailServer()

    def set_server(self, server: Server):
        # 2 - introduce it to its server on the client side
        self.server = server

    def send(self, d: Dict):
        # 3 - send a message from the client
        return self.server.send(self.route_name, d)

    def handle(self, sent_dict: Dict[Text, Text]):
        # 4 - handle a message on the server
        return self._handle_dict(sent_dict)

    @abc.abstractmethod
    def _handle_dict(self, sent_dict: Dict[Text, Text]):
        pass


class SingleFieldPostDictAction(PostDictAction):
    def __init__(self, server: Server, route_name: Text, request_field_name: Text):
        super().__init__(server, route_name)
        self.request_field_name = request_field_name

    def _handle_dict(self, sent_dict: Dict[Text, Text]):
        if self.request_field_name not in sent_dict:
            raise ValueError(f"Couldn't find field {self.request_field_name} in your request which included fields: "
                             f"{sent_dict.keys()}")
        return self._handle_field(sent_dict[self.request_field_name])

    def _handle_field(self, sent_value: Text):
        """This is essentially an abstract method which gets replaced by a passed in function."""
        raise NotImplementedError("Set your ")

    def send(self, value_to_send: Text):
        if not isinstance(value_to_send, str):
            raise ValueError(f"Expected str, got {type(value_to_send)}.")
        return super().send({self.request_field_name: value_to_send})


class FailServer(Server):
    def __init__(self):
        super().__init__('', -1)

    """A dummy server which always fails."""
    def send(self, url_path: Text, d: Dict) -> requests.Response:
        raise NotImplementedError()


class ActionFactory:
    pass

    @classmethod
    def single_field_post_dict_action(
            cls,
            server: Server,
            route_name: Text,
            request_field_name: Text,
            handle_value_fn: Callable[[Text], requests.Response],
    ):
        action = SingleFieldPostDictAction(server, route_name, request_field_name)
        action._handle_field = handle_value_fn
        return action


class MyServer(Server):
    def __init__(self, ):


# want to write:
add_authoried_key_action = ActionFactory.single_field_post_dict_action(
    server=server,

)



class AddAuthorizedKeyAction(SingleFieldPostDictAction):
    def __init__(self, server: Server):
        super().__init__(server, route_name='add_authorized_key', request_field_name='public_key')

    def _handle_field(self, sent_value: Text):




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
