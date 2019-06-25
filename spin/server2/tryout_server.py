import abc

from flask import Flask, request, jsonify
import requests
from typing import Dict, Text, Union, List, Tuple

from spin import utils

app = Flask(__name__)


class Action:
    def __init__(self, route='my_route'):
        self.route = route
        self.server = FailServer()
        self.message = 'muy message'

    @abc.abstractmethod
    def local(self) -> Dict:
        pass

    @abc.abstractmethod
    def remote(self, d: Dict) -> Dict:
        pass

    def get_name_on_server(self) -> Text:
        return utils.camel_2_snake(self.__class__.__name__)

    def set_server(self, server: 'Server'):
        self.server = server

    def __call__(self, *args, **kwargs):
        return self.server.run_action(self)


class SingleValueAction(Action):
    """Special case of an action which is set to deal with only one value in a dict rather than the whole dict."""
    FIELD_NAME = 'val'

    def local(self) -> Dict:
        return {self.FIELD_NAME: self.local_value()}

    def remote(self, d: Dict) -> Dict:
        return {self.FIELD_NAME: self.remote_value(d[self.FIELD_NAME])}

    @abc.abstractmethod
    def local_value(self) -> Text:
        pass

    @abc.abstractmethod
    def remote_value(self, value: Text) -> Text:
        pass


class Server:
    enum = None

    def __init__(self, host: Text, port: int, actions=Union[List[Action], Tuple[Action], Dict[Text, Action]]):
        self.host = host
        self.port = port

        # check input actions for type
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

        # ensure unique routes
        routes = [a.route for a in actions]
        if not len(set(routes)) == len(routes):
            raise ValueError(f"The routes on your actions must be unique but you passed in "
                             f"actions with routes {routes}")

        # set actions
        if len(actions) == 0:
            self.actions = {}
        else:
            # confirm list item types
            for ind, action in enumerate(actions):
                if not isinstance(action, Action):
                    raise ValueError(f"Item {ind} in actions is type {type(action)} but expected "
                                     f"{Action.__class__.__name__}")

            self.actions = {action.get_name_on_server(): action for action in actions}

        # register actions
        for action in self.actions.values():
            self._register_action(action)

    def _register_action(self, action: Action):
        action.set_server(self)

        leading_slash = '' if action.route.startswith('/') else '/'
        rule = f'{leading_slash}{action.route}'

        @app.route(rule=rule, methods=['POST'])
        def handle():
            print('handling it')
            request_data = request.get_json(force=True)
            return jsonify(action.remote(request_data))

    def run_action(self, a: Action) -> requests.Response:
        url = f'http://{self.host}:{self.port}/{a.route}'
        response = requests.post(url=url, json=a.local())
        return response

    def serve(self):
        app.run(host=self.host, port=self.port, debug=True)

    @abc.abstractmethod
    def _set_actions(self):
        """Run in the init.  Set actions to self."""
        pass



class FailServer(Server):
    """A dummy server which always fails."""
    def __init__(self):
        super().__init__('', -1, [])

    def run_action(self, a: Action) -> requests.Response:
        raise NotImplementedError()



