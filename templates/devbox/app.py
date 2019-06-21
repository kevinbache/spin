import time

from flask import Flask
from flask import jsonify

app = Flask(__name__)

@app.route('/')
def hello_world():
    # target = os.environ.get('TARGET', 'World')
    # return 'Hello {}!\n'.format(target)
    d = {'resp': 'hello world! time: {}'.format(time.time())}
    return jsonify(d)

    # https://stackoverflow.com/questions/13081532/return-json-response-from-flask-view
    # response = app.response_class(
    #     response=json.dumps(data),
    #     status=200,
    #     mimetype='application/json'
    # )
    # return response


if __name__ == "__main__":
    # NOTE: DRY VIOLATION.  8080 shows up here, Dockerfile, and k8s yaml
    app.run(debug=True, host='0.0.0.0', port=80)
