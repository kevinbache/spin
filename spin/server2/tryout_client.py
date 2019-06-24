import requests
from spin.server2 import tryout_server, actions

# from flask import Flask
#
#
# app = Flask(__name__)

if __name__ == '__main__':
    s = tryout_server.Server(host='localhost', port=5000)
    a = actions.Action()
    url = f'http://{s.host}:{s.port}/{a.route}'
    print(url)
    response = requests.post(url=url, json={'msg': 'this is my message!'})
    print(response)
    print(response.text)

