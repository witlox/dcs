from flask import Flask, request, jsonify, Response

from flask.json import dumps
from flask_swagger import swagger

from controller.ilm.repository import AmiRepository
from controller.exceptions import ApplicationException

api = Flask(__name__)

api.config['REPOSITORY'] = AmiRepository()

@api.route("/")
def spec():
    swag = swagger(api)
    swag['info']['version'] = "0.9"
    swag['info']['title'] = "ILM"
    return jsonify(swag)

@api.route('/amis', methods=['GET'])
def get_amis():
    """
        List currently registered AMI's
        ---
        tags:
        - amis
        responses:
            200:
                description: List of AMI id's
    """
    repository = api.config['REPOSITORY']
    return Response(dumps(repository.get_all_amis()), mimetype='application/json')

@api.route('/amis', methods=['POST'])
def add_amis():
    """
        Register a new AMI
        ---
        tags:
        - amis
        parameters:
          - in: body
            name: body
            schema:
              id: AMI
              required:
                - name
              optional:
                - username
                - password
                - public_key
                - private_key
              properties:
                name:
                  type: string
                  description: AMI id
                username:
                  type: string
                  description: username for AMI access
                password:
                  type: string
                  description: password for AMI access
                public_key:
                  type: string
                  description: public key for AMI access
                private_key:
                  type: string
                  description: private key for AMI access
        responses:
            200:
                description: new AMI registered
    """
    data = request.get_json(force=True)
    repository = api.config['REPOSITORY']
    aid = repository.insert_ami(data['name'], data['credentials'])
    return Response(dumps(aid), mimetype='application/json')

@api.route('/amis', methods=['DELETE'])
def remove_amis(name):
    """
        Unregister an AMI
        ---
        tags:
        - amis
        parameters:
          - in: body
            name: body
            schema:
              id: AMI
              required:
                - name
              properties:
                name:
                  type: string
                  description: AMI id
        responses:
            200:
                description: AMI unregistered
            500:
                description: could not unregister AMI (maybe it doesn't exist)
    """
    repository = api.config['REPOSITORY']
    res = repository.delete_ami(name)
    if res:
        return Response(dumps(res), mimetype='application/json')
    else:
        raise ApplicationException('Could not delete %s' % name)


# register error handlers

@api.errorhandler(ApplicationException)
def handle_application_exception(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response
