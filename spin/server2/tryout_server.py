from flask import Flask, request, jsonify
from typing import Text

from spin.server2 import actions

app = Flask(__name__)


class Server:
    def __init__(self, host: Text, port: int):
        self.host = host
        self.port = port

    def serve(self):
        app.run(host=self.host, port=self.port, debug=True)

    @staticmethod
    def register_action(action: actions.Action):
        @app.route(rule=f'/{action.route}', methods=['POST'])
        def handle():
            print('handling it')
            request_data = request.get_json(force=True)
            print(f"request_data = {request_data}")
            return jsonify(action.make_dict_to_send())


if __name__ == '__main__':
    s = Server(host='localhost', port=5000)
    a = actions.Action()
    s.register_action(a)
    s.serve()
