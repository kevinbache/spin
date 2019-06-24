import dataclasses
import enum
from flask import Flask, request, jsonify
import requests
from typing import Dict, Text, Union, List, Tuple, Iterable

from spin import utils

app = Flask(__name__)


class Action:
    def __init__(self, route='my_route'):
        self.route = route
        self.server = FailServer()
        self.message = 'muy message'

    # TODO: Handle passing arguments to this method
    def make_client_to_server_dict(self) -> Dict:
        return {'make_client_to_server_dict action message': self.message}

    def make_server_to_client_dict(self, d: Dict) -> Dict:
        return {'make_server_to_client_dict action message': self.message}

    def get_name_on_server(self) -> Text:
        return utils.camel_2_snake(self.__class__.__name__)

    def set_server(self, server: 'Server'):
        self.server = server

    def __call__(self, *args, **kwargs):
        return self.server.client_to_server(self)


class Server:
    enum = None

    def __init__(self, host: Text, port: int, actions=Union[List[Action], Tuple[Action], Dict[Text, Action]]):
        self.host = host
        self.port = port

        # if isinstance(actions, enum.EnumMeta):
        #     self.actions = actions
        # elif dataclasses.is_dataclass(actions):
        #     self.actions = actions
        if isinstance(actions, dict):
            for k in actions.keys():
                if not isinstance(k, Text):
                    raise ValueError(f"If actions is a dict, it should map action name to action.  "
                                     f"Got a key of type {type(k)})")
            for v in actions.values():
                if not isinstance(v, Action):
                    raise ValueError(f"If actions is a dict, it should map action name to action.  "
                                     f"Got a value of type {type(v)})")
        elif not isinstance(actions, (list, tuple)):
            raise ValueError(f"Expected a list or tuple of {Action.__class__.__name__}s.  Got {type(actions)}.")

        if len(actions) == 0:
            self.actions = {}
        else:
            # confirm list item types
            for ind, action in enumerate(actions):
                if not isinstance(action, Action):
                    raise ValueError(f"Item {ind} in actions is type {type(action)} but expected "
                                     f"{Action.__class__.__name__}")

            self.actions = {action.get_name_on_server(): action for action in actions}

        for action in self.actions.values():
            self._register_action(action)

    def _register_action(self, action: Action):
        action.set_server(self)

        @app.route(rule=f'/{action.route}', methods=['POST'])
        def handle():
            print('handling it')
            request_data = request.get_json(force=True)
            print(f"request_data = {request_data}")
            return jsonify(action.make_server_to_client_dict(request_data))

    def client_to_server(self, a: Action) -> requests.Response:
        url = f'http://{self.host}:{self.port}/{a.route}'
        response = requests.post(url=url, json=a.make_client_to_server_dict())
        return response

    def serve(self):
        app.run(host=self.host, port=self.port, debug=True)


class FailServer(Server):
    """A dummy server which always fails."""
    def __init__(self):
        super().__init__('', -1, [])

    def client_to_server(self, a: Action) -> requests.Response:
        raise NotImplementedError()


def get_server() -> Server:
    return Server(host='localhost', port=5000, actions=[Action()])


if __name__ == '__main__':
    s = get_server()
    s.serve()
