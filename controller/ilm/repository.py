import json
import pickle
import logging
import threading
import redis
from logging.config import dictConfig


class AmiRepository(threading.Thread):
    def __init__(self):
        try:
            with open('logging.json') as jl:
                dictConfig(json.load(jl))
            self.client = redis.Redis('db')
        except Exception, e:
            logging.exception('Problem instantiating ami repository (%s)' % e)

    def get_all_amis(self):
        return [ami_key for ami_key in self.client.keys() if ami_key.startswith('ami-')]  # Redis keys(pattern='*') does not filter at all.

    def insert_ami(self, ami, username, private_key):
        logging.info('registering new AMI %s with user %s' % (ami, username))
        return self.client.set(ami, pickle.dumps([username, private_key]))

    def delete_ami(self, ami):
        logging.info('removing AMI %s' % ami)
        return self.client.delete(ami)

    def get_all_workers(self):
        result = []
        for key in [worker_key for worker_key in self.client.keys() if worker_key.startswith('jm-')]:  # Redis keys(pattern='*') does not filter at all.
            worker = pickle.loads(self.client.get(key))
            result.append([key, worker.job_id, worker.batch_id, worker.reservation, worker.instance, worker.request_time, worker.ip_address])
        return result
