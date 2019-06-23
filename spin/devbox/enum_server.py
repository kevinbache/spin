import enum
from typing import Text

from flask import Flask

app = Flask(__name__)




class Action:
    def __init__(self, message: Text):
        self.server = None
        self.message = message

    def __call__(self, *args, **kwargs):
        print(self.message)

    def set_server(self, server: 'TestServer'):
        self.server = server

    def local_half(self, *args, **kwargs):
        pass

    def remote_half(self, *args, **kwargs):


class TestServer(enum.Enum):
    action1 = Action('action1_message')
    action2 = Action('action2_message')

    def __new__(cls, *args, **kwargs):
        x

    def __call__(self, *args, **kwargs):



if __name__ == '__main__':
    TestServer.action1()

