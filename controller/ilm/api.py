from flask import Flask, request, jsonify, Response

from flask.json import dumps
from flask_autodoc import Autodoc

from repository import AmiRepository

api = Flask(__name__)
auto = Autodoc(api)

api.config['REPOSITORY'] = AmiRepository()

def __get_amis__():
    repository = api.config['REPOSITORY']
    return Response(dumps(repository.get_all_amis()), mimetype='application/json')

def __get_ami__(name):
    repository = api.config['REPOSITORY']
    return Response(dumps(repository.get_ami(name)), mimetype='application/json')

def __add_amis__(request):
    data = request.get_json(force=True)
    repository = api.config['REPOSITORY']
    aid = repository.insert_ami(data['name'], data['username'], data['private_key'])
    return Response(dumps(aid), mimetype='application/json')

def __remove_amis__(name):
    repository = api.config['REPOSITORY']
    res = repository.delete_ami(name)
    if res:
        return Response(dumps(res), mimetype='application/json')
    else:
        raise ApplicationException('Could not delete %s' % name)

# actual api :P

@api.route("/")
def documentation():
    return auto.html()

@api.route('/amis', methods=['GET'])
@auto.doc()
def get_amis():
    """ list currently registered AMI's """
    return __get_amis__()


@api.route('/ami/<name>', methods=['GET'])
@auto.doc()
def get_ami(name):
    """ get requested AMI credentials """
    return __get_ami__(name)


@api.route('/amis', methods=['POST'])
@auto.doc()
def add_amis():
    """
    register a new AMI
    :argument AMI (json) => {name, username, private key (pem)}}
    """
    return __add_amis__(request)

@api.route('/amis/<name>', methods=['DELETE'])
@auto.doc()
def remove_amis(name):
    """ unregister an AMI """
    return __remove_amis__(name)

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

@api.errorhandler(ApplicationException)
def handle_application_exception(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

