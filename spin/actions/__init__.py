import abc

from flask import Flask, request, jsonify
import requests
from typing import Dict, Text, Any

app = Flask(__name__)


# Dict type passed from client to server and back.
TextDict = Dict[Text, Any]


class Action:
    """An `Action` is essentially a remote procedure call.
    Essentially you can think of it as a function which has been split in two.
    It has a local half, a remote half, and can send a dictionary message between the two."""
    def __init__(self, route='my_route'):
        self.route = route
        self.server = FailServer()

    def __call__(self):
        """Run this action"""
        return self.server.run_action(self)

    def set_server(self, server: 'Server'):
        if server.as_client:
            self._verify_on_client()
        else:
            self._verify_on_server()

        self.server = server

    def _verify_on_client(self):
        """Implement initialization verifications here that only run on the local side."""
        pass

    def _verify_on_server(self):
        """Implement initialization verifications here that only run on the remote side."""
        pass

    @abc.abstractmethod
    def local(self) -> TextDict:
        """Run the local half of this Action.  If you want to take arguments, pass them in through __init__.
        Return the Dict that will be passed to the remote half.

        TODO: pass *args, **kwargs from __call__ rather than forcing init pass?
        """
        pass

    @abc.abstractmethod
    def remote(self, d: TextDict) -> TextDict:
        """The method which runs remotely.  It takes in the dict that was passed
        from the local half does something on the remote server, and then returns another dict to send back."""
        pass


class SingleValueAction(Action):
    """Special case of an action which is set to only pass a single string rather than a dict."""
    FIELD_NAME = 'val'

    def local(self) -> Dict:
        return {self.FIELD_NAME: self._local_single_value()}

    def remote(self, d: Dict) -> Dict:
        return {self.FIELD_NAME: self._remote_single_value(d[self.FIELD_NAME])}

    @abc.abstractmethod
    def _local_single_value(self) -> Text:
        pass

    @abc.abstractmethod
    def _remote_single_value(self, value: Text) -> Text:
        pass


class Server:
    """Used on the local side as a stub to send Actions to the remote side
    and on the remote side as a simple server for running the remote side of those actions.

    Here, a Server is essentially just a host, port, and collection of actions.

    It creates and owns the Flask routes for its actions and can run an action locally before
    passing the action's message to its remote counterpart to be completed.
    """
    def __init__(
            self,
            as_client=True,
            host: Text = '0.0.0.0',
            port: int = 5000,
    ):
        """Create a server.

        Args:
            host: Text
                The IP address at which to run this server.
                Switch to '127.0.0.1' if you want the (more secure) option to only have the
                computer accessible from your local machine, not anyone on your network.
            port: int
                The port at which to run this server.  Flask default is 5000.
        """
        self.host = host
        self.port = port

        self.as_client = as_client

        self.action_name_to_action = self._set_actions()

        # ensure unique routes
        routes = [a.route for a in self.action_name_to_action.values()]
        if not len(set(routes)) == len(routes):
            raise ValueError(f"The routes on your actions must be unique but you passed in "
                             f"actions with routes {routes}")

        # register actions
        for action in self.action_name_to_action.values():
            self._register_action(action)

        if not as_client:
            self.debug_serve()

    def _register_action(self, action: Action):
        """Register this action with this server."""

        action.set_server(self)

        leading_slash = '' if action.route.startswith('/') else '/'
        rule = f'{leading_slash}{action.route}'

        @app.route(rule=rule, methods=['POST'])
        def handle():
            print('handling it')
            request_data = request.get_json(force=True)
            return jsonify(action.remote(request_data))

    def run_action(self, a: Action) -> requests.Response:
        """Run both the local and remote halves of the given Action."""
        url = f'http://{self.host}:{self.port}/{a.route}'
        response = requests.post(url=url, json=a.local())
        return response

    def debug_serve(self):
        """Run this server.  In debug mode.  For actually running this server, use gunicorn."""
        print(f"self.host = {self.host}")
        print(f"self.port = {self.port}")
        app.run(host=self.host, port=self.port, debug=True)

    @abc.abstractmethod
    def _set_actions(self) -> Dict[Text, Action]:
        """Run in the init.  Set actions to self."""
        pass


class FailServer(Server):
    """A dummy server which always fails."""

    def _set_actions(self) -> Dict[Text, Action]:
        return {}

    def __init__(self):
        super().__init__(as_client=True, host='', port=-1)

    def run_action(self, a: Action) -> requests.Response:
        raise NotImplementedError()

