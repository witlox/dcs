from json import dumps
from flask import Flask, Response, jsonify, request
from flask_autodoc import Autodoc

from repository import JobRepository

app = Flask(__name__)
auto = Autodoc(app)

app.config['REPOSITORY'] = JobRepository()

def __get_jobs__():
    repository = app.config['REPOSITORY']
    return Response(dumps(repository.get_all_jobs()), mimetype='application/json')

def __add_jobs__(data):
    jdata = data.get_json(force=True)
    repository = app.config['REPOSITORY']
    aid = repository.insert_job(jdata['ami'], jdata['instance_type'])
    return Response(dumps(aid), mimetype='application/json')

def __remove_jobs__(name):
    repository = app.config['REPOSITORY']
    res = repository.delete_job(name)
    if res:
        return Response(dumps(res), mimetype='application/json')
    else:
        raise ApplicationException('Could not delete %s' % name)

def __get_job_state__(name):
    repository = app.config['REPOSITORY']
    return Response(dumps(repository.get_job_state(name)), mimetype='application/json')

def __set_job_state__(name, new_state):
    repository = app.config['REPOSITORY']
    return Response(dumps(repository.set_job_state(name, new_state)), mimetype='application/json')

def __batch_submit__(data, max_nodes):
    jdata = data.get_json(force=True)
    repository = app.config['REPOSITORY']
    aid = repository.execute_batch(max_nodes, jdata['ami'], jdata['instance_type'])
    return Response(dumps(aid), mimetype='application/json')

# actual api :P

@app.route('/')
def documentation():
    return auto.html()

@app.route('/jobs', methods=['GET'])
@auto.doc()
def get_jobs():
    """ list currently registered jobs """
    return __get_jobs__()


@app.route('/jobs', methods=['POST'])
@auto.doc()
def add_jobs():
    """
    register a new job
    :argument JOB (json) => {ami, instance_type}
    """
    return __add_jobs__(request)

@app.route('/jobs/<name>', methods=['DELETE'])
@auto.doc()
def remove_jobs(name):
    """ remove a job """
    return __remove_jobs__(name)

@app.route('/jobs/<name>/state', methods=['GET'])
@auto.doc()
def get_state(name):
    """ get job state """
    return __get_job_state__(name)

@app.route('/jobs/<name>/state/<new_state>', methods=['POST'])
@auto.doc()
def set_state(name, new_state):
    """ set job state """
    return __set_job_state__(name, new_state)

@app.route('/batch/<int:max_nodes>', methods=['POST'])
@auto.doc()
def batch_submit(max_nodes):
    """
    submit batch of jobs, with maximum nodes to use
    :argument BATCH (json) => {ami, instance_type}
    """
    return __batch_submit__(request, max_nodes)

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

