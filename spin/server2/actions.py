from typing import Dict


class Action:
    def __init__(self, route='my_route”'):
        self.route = route
        self.server = None
        self.message = 'muy message'

    def make_dict_to_send(self) -> Dict:
        return {'action message from client': self.message}

