from spin import server
from spin.server import actions

if __name__ == '__main__':
    s = server.Server('localhost', 5000, [actions.AddKnownKeyAction()])
    out = server.actions.AddKnownKeyAction('~/.ssh/id_rsa.pub')
    print(out)
    print(out.data)

