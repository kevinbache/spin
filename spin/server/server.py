import abc
import enum
import flask
from typing import Dict, Text, List, Optional, Any

import requests


TextDict = Dict[Text, Any]


class Server:
    def __init__(self, host: Text, port: int, actions: List['Action'], flask_app: flask.Flask):
        self.host = host
        self.port = port
        self.protocol = 'https'

        enum_dict = {}
        for act in actions:
            act.register_server(self)
            enum_dict[act.__class__.__name__] = act

        self.actions = enum.Enum('actions', enum_dict)
        self.flask_app = flask_app

    def get_url(self, path: Text):
        return f'{self.protocol}://{self.host}:{self.port}/{path}'

    def serve(self):
        # TODO: Secure me
        self.flask_app.run(debug=True)

    @abc.abstractmethod
    def client_to_server(self, route: Text, dict_to_send: Dict) -> requests.Response:
        return requests.post(self.get_url(route), json=dict_to_send)


class FailServer(Server):
    def __init__(self):
        super().__init__('', -1, [], None)

    """A dummy server which always fails."""
    def client_to_server(self, route: Text, dict_to_send: Dict) -> requests.Response:
        raise NotImplementedError()


class Action(abc.ABC):
    def __init__(self, route: Text):
        self.route = route
        self.server = FailServer()

        self.app = flask.Flask(__name__)

    def __call__(self, *args, **kwargs):
        dict_to_send = self._on_client()
        return self._send_to_server(dict_to_send)

    @abc.abstractmethod
    def _on_client(self, *args, **kwargs) -> TextDict:
        pass

    def _send_to_server(self, dict_to_send: TextDict):
        return requests.post(self.server.get_url(self.route), json=dict_to_send)

    @abc.abstractmethod
    def _on_server(self, received_dict: Dict) -> Optional[requests.Response]:
        pass

    def _on_server_outer(self, received_dict: Dict) -> Optional[requests.Response]:
        response = self._on_server(received_dict)
        if response is None:
            return requests.Response()

    def register_server(self, s: Server):
        self.server = s

        @self.server.flask_app.route(self.route)
        def handle():
            request_data = flask.request.get_json(force=True)
            self._on_server(request_data)


class SingleFieldAction(Action):
    FIELD_NAME = 'val'

    def _on_client(self, *args, **kwargs) -> TextDict:
        return {self.FIELD_NAME: self._on_client_value()}

    @abc.abstractmethod
    def _on_client_value(self, *args, **kwargs) -> Text:
        pass

    def _on_server(self, received_dict: Dict) -> Optional[requests.Response]:
        return self._on_server_value(received_dict[self.FIELD_NAME])

    @abc.abstractmethod
    def _on_server_value(self, value: Any) -> Optional[requests.Response]:
        pass





# import abc
# import enum
# from pathlib import Path
#
# import requests
# from typing import List, Dict, Text
#
# TextDict = Dict[Text, Text]
#
#
# class Action:
#     @abc.abstractmethod
#     def on_server(self, request_data: TextDict):
#         pass
#
#     @abc.abstractmethod
#     def __call__(self, *args, **kwargs) -> TextDict:
#         """Called on client"""
#         pass
#
#
# class DictPrintAction(Action):
#     def on_server(self, request_data: TextDict):
#         print(request_data)
#
#     def __call__(self, *args, **kwargs):
#         return {'key': 'value!'}
#
#
# class Actions(enum.Enum):
#     def __init__(self, action: Action):
#         self.action = action
#
#     def __call__(self, *args, **kwargs):
#         self.action.__call__(*args, **kwargs)
#
#
# class AddKeyAction(Action):
#     def on_server(self, request_data: TextDict):
#         print(request_data)
#
#     def __call__(self, public_key_filename: Text) -> TextDict:
#         return {'public_key': Path(public_key_filename).read_text()}
#
#
# class DevBoxActions(Actions):
#     add_key = Action()
#
#
# class Server:
#     """Acts as both client-side server stub and server-side handler.
#
#     TODO: How to init server with same actions on both sides?  Subclass and override init?  Factory?
#     """
#     def __init__(self, actions: Dict[Text, Action]):
#         self.actions = actions
#
#
# if __name__ == '__main__':
#     # server = Server(
#     #     actions={'add_key': DictPrintAction()}
#     # )
#     #
#     # server.actions
#
#     DevBoxActions.add_key.