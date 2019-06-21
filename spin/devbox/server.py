from flask import Flask, render_template, request, url_for, jsonify

app = Flask(__name__)


@app.route('/add_auth_key', methods=['POST'])
def my_test_endpoint():
    request_data = request.get_json(force=True)
    # force=True, above, is necessary if another developer
    # forgot to set the MIME type to 'application/json'
    print(f"request_data               = {request_data}")
    print(f"request_data['public_key'] = {request_data['public_key']}")
    out = {'republished_key': 'AAAAAAAAAAAAAA ' + request_data['public_key']}
    return jsonify(out)


if __name__ == '__main__':
    app.run(debug=True)


# from flask import Flask
#
# app = Flask(__name__)
#
#
# @app.route("/")
# def home():
#     return "Hello, World!"
#
#
# @app.route("/salvador")
# def salvador():
#     return "Hello, Salvador"
#
#
# if __name__ == "__main__":
#     app.run(debug=True)
