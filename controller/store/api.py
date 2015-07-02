import os
from flask_autodoc import Autodoc
from flask import Flask, request, jsonify, make_response

api = Flask(__name__)
auto = Autodoc(api)

if os.environ.has_key('store'):
    api.config['settings'] = os.environ['store']
else:
    if not os.path.exists('/tmp/store'):
        os.mkdir('/tmp/store')
    api.config['settings'] = '/tmp/store'

def __upload__(file_name):
    if request.headers['Content-Type'] == 'application/octet-stream':
        path = os.path.join(api.config['settings'], file_name)
        if os.path.exists(path):
            raise ApplicationException('File (%s) already exists, will not overwrite' % file_name)
        with open(path, 'wb') as f:
            f.write(request.data)
        return 'Upload received!'
    raise ApplicationException('No data in upload request')

def __download__(file_name):
    path = os.path.join(api.config['settings'], file_name)
    if not os.path.exists(path):
        raise ApplicationException('Requested file (%s) does not exist' % file_name)
    with open(path, 'rb') as f:
        response = make_response(path)
        response.headers['Content-Type'] == 'application/octet-stream'
        response.headers["Content-Disposition"] = "attachment; filename=%s" % file_name
        response.data = f.read()
    return response

def __deleter__(file_name):
    path = os.path.join(api.config['settings'], file_name)
    if not os.path.exists(path):
        raise ApplicationException('Requested file (%s) does not exist' % file_name)
    os.remove(path)
    return 'ok'

# actual api here :P
@api.route('/')
def documentation():
    return auto.html()

@api.route('/<file_name>', methods=['POST'])
@auto.doc()
def upload(file_name):
    """ upload a file to the store """
    return __upload__(file_name)

@api.route('/<file_name>', methods=['GET'])
@auto.doc()
def download(file_name):
    """ download a file from the store """
    return __download__(file_name)

@api.route('/<file_name>', methods=['DELETE'])
@auto.doc()
def delete(file_name):
    """ delete a file from the store """
    return __deleter__(file_name)


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
