from json import dumps
import os
import shutil
import zipfile
from flask_autodoc import Autodoc
from flask import Flask, request, jsonify, make_response, Response

app = Flask(__name__)
auto = Autodoc(app)

if os.environ.has_key('store'):
    app.config['settings'] = os.environ['store']
else:
    if not os.path.exists('/tmp/store'):
        os.mkdir('/tmp/store')
    app.config['settings'] = '/tmp/store'

def __upload__(file_name):
    if request.headers['Content-Type'] == 'application/octet-stream':
        path = os.path.join(app.config['settings'], file_name)
        if os.path.exists(path):
            raise ApplicationException('File (%s) already exists, will not overwrite' % file_name)
        with open(path, 'wb') as f:
            f.write(request.data)
        return 'Upload received!'
    raise ApplicationException('No data in upload request')

def __download__(file_name):
    path = os.path.join(app.config['settings'], file_name)
    if not os.path.exists(path):
        raise ApplicationException('Requested file (%s) does not exist' % file_name)
    with open(path, 'rb') as f:
        response = make_response(path)
        response.headers['Content-Type'] == 'application/octet-stream'
        response.headers["Content-Disposition"] = "attachment; filename=%s" % file_name
        response.data = f.read()
    return response

def __deleter__(file_name):
    path = os.path.join(app.config['settings'], file_name)
    if not os.path.exists(path):
        raise ApplicationException('Requested file (%s) does not exist' % file_name)
    os.remove(path)
    return 'ok'

def __get_all_files__():
    root = app.config['settings']
    if not root or not os.path.exists(root) or not os.path.isdir(root):
        raise ApplicationException('Something wrong with our filesystem (%s)' % root)
    return Response(dumps([f for f in os.listdir(root) if os.path.isfile(os.path.join(root, f))]), mimetype='application/json')

def __extract__(file_name):
    path = os.path.join(app.config['settings'], file_name)
    if not os.path.exists(path):
        raise ApplicationException('Requested file (%s) does not exist' % file_name)
    file_path = os.path.join(app.config['settings'], os.path.splitext(file_name)[0])
    if os.path.exists(file_path):
        shutil.rmtree(file_path)
    os.mkdir(file_path)
    os.chdir(file_path)
    with zipfile.ZipFile('../%s' % file_name) as zf:
        zf.extractall()
    created = []
    for d in next(os.walk('.'))[1]:
        shutil.make_archive('../job-%s' % d, 'zip', d)
        created.append('job-%s' % str(d))
    os.chdir('..')
    shutil.rmtree(os.path.splitext(file_name)[0])
    return Response(dumps(created), mimetype='application/json')

def __compress__(data, file_name):
    jdata = data.get_json(force=True)
    file_names = jdata['file_names']
    file_path = os.path.join(app.config['settings'], os.path.splitext(file_name)[0])
    if os.path.exists(file_path):
        shutil.rmtree(file_path)
    os.mkdir(file_path)
    os.chdir(file_path)
    for name in file_names:
        os.mkdir(os.path.splitext(name)[0])
        os.chdir(os.path.splitext(name)[0])
        with zipfile.ZipFile('../../%s' % name) as zf:
            zf.extractall()
        os.chdir('..')
    shutil.make_archive('../%s' % file_name, 'zip')
    os.chdir('..')
    shutil.rmtree(os.path.splitext(file_name)[0])
    for name in file_names:
        os.remove(os.path.join(app.config['settings'], name))
    return 'ok'


# actual api here :P
@app.route('/')
def documentation():
    return auto.html()

@app.route('/<file_name>', methods=['POST'])
@auto.doc()
def upload(file_name):
    """ upload a file to the store """
    return __upload__(file_name)

@app.route('/<file_name>', methods=['GET'])
@auto.doc()
def download(file_name):
    """ download a file from the store """
    return __download__(file_name)

@app.route('/<file_name>', methods=['DELETE'])
@auto.doc()
def delete(file_name):
    """ delete a file from the store """
    return __deleter__(file_name)

@app.route('/files/', methods=['GET'])
@auto.doc()
def list_files():
    """ List all files in the store """
    return __get_all_files__()

@app.route('/extract/<file_name>', methods=['GET'])
def extract(file_name):
    """ extract a file on the store """
    return __extract__(file_name)

@app.route('/compress/<file_name>', methods=['POST'])
def compress(file_name):
    """ compress multiple archives into one archive on the store """
    return __compress__(request, file_name)


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
