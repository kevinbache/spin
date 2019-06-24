from spin.server2 import tryout_server


if __name__ == '__main__':
    s = tryout_server.get_server()

    response = s.actions['action']()
    print(response)
    print(response.text)

