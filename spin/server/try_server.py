import flask

from spin.server import server, actions

app = flask.Flask(__file__)

if __name__ == '__main__':
    s = server.Server('localhost', 5000, [actions.AddKnownKeyAction()], app)
    s.serve()
