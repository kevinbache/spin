from spin.server2 import my_actions


if __name__ == '__main__':
    s = my_actions.get_server()

    response = s.actions['send_public_key']()
    print(response)
    print(response.text)
