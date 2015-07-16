from flask import Flask, request, jsonify, Response
from flask.json import dumps
from flask_autodoc import Autodoc

from repository import AmiRepository

app = Flask(__name__)
auto = Autodoc(app)

app.config['REPOSITORY'] = AmiRepository()

def __get_amis__():
    repository = app.config['REPOSITORY']
    return Response(dumps(repository.get_all_amis()), mimetype='application/json')

def __get_ami__(name):
    repository = app.config['REPOSITORY']
    return Response(dumps(repository.get_ami(name)), mimetype='application/json')

def __add_amis__(request):
    data = request.get_json(force=True)
    repository = app.config['REPOSITORY']
    aid = repository.insert_ami(data['name'], data['username'], data['private_key'])
    return Response(dumps(aid), mimetype='application/json')

def __remove_amis__(name):
    repository = app.config['REPOSITORY']
    res = repository.delete_ami(name)
    if res:
        return Response(dumps(res), mimetype='application/json')
    else:
        raise ApplicationException('Could not delete %s' % name)

def __get_all_workers__():
    repository = app.config['REPOSITORY']
    return Response(dumps(repository.get_all_workers()), mimetype='application/json')

# actual api :P

@app.route('/', defaults={'path': ''})
def documentation():
    return auto.html()

@app.route('/amis', methods=['GET'])
@auto.doc()
def get_amis():
    """ list currently registered AMI's """
    return __get_amis__()


@app.route('/ami/<name>', methods=['GET'])
@auto.doc()
def get_ami(name):
    """ get requested AMI credentials """
    return __get_ami__(name)


@app.route('/amis', methods=['POST'])
@auto.doc()
def add_amis():
    """
    register a new AMI
    :argument AMI (json) => {name, username, private key (pem)}}
    """
    return __add_amis__(request)

@app.route('/amis/<name>', methods=['DELETE'])
@auto.doc()
def remove_amis(name):
    """ unregister an AMI """
    return __remove_amis__(name)

@app.route('/workers', methods=['GET'])
@auto.doc()
def get_workers():
    """ list currently registered workers """
    return __get_all_workers__()


# register error handlers
class ApplicationException(Exception):
    status_code = 500

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@app.errorhandler(ApplicationException)
def handle_application_exception(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

