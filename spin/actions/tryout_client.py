from spin.actions import my_actions


if __name__ == '__main__':
    s = my_actions.DevBoxServer(host='localhost', port=5000)
    response = s.send_public_key()

    print(response)
    print(response.text)


