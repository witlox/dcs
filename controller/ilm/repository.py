from datetime import datetime
import json
import pickle
import logging
import threading
import redis
import aws
from logging.config import dictConfig
from machine_midwife import MachineMidwife

dictConfig(json.loads('logging.json'))

class AmiRepository(threading.Thread):
    def __init__(self):
        try:
            self.client = redis.Redis('db')
            self.pubsub = self.client.pubsub()
            self.pubsub.subscribe(['jobs'])
            self.midwife = MachineMidwife(self.client)
            self.start()
        except Exception:
            logging.exception('Cannot connect with the database server')
            raise

    def get_all_amis(self):
        return self.client.keys('ami*')

    def get_ami(self, name):
        return pickle.dumps(self.client.get(name))

    def insert_ami(self, ami, username, private_key):
        logging.info('registering new AMI %s with user %s' % (ami, username))
        return self.client.set(ami, pickle.dumps([username, private_key]))

    def delete_ami(self, ami):
        logging.info('removing AMI %s' % ami)
        return self.client.delete(ami)

    def run(self):
        for item in self.pubsub.listen():
            if item['data'] == 'KILL':
                self.pubsub.unsubscribe()
                logging.info('unsubscribed and finished')
                break
            else:
                self.job_changed(item['data'])

    # state machine for virtual machine manager
    def job_changed(self, job_id):
        if self.client.exists(job_id):
            job = pickle.loads(self.client.get(job_id))
            if job[2] == 'received':
                worker, reservation = aws.start_machine(job[0], job[1])
                if worker:
                    job[2] = 'requested'
                    self.client.set(worker, pickle.dumps([job_id, reservation, None, 'requested', datetime.now()]))
                else:
                    job[2] = 'ami request failed'
                self.client.set(job_id, pickle.dumps(job))
                self.client.publish('jobs', job_id)
        else:
            for worker in self.client.keys('jm-*'):
                worker_state = pickle.loads(self.client.get(worker))
                if worker_state[0] == job_id and worker_state[2] is not None and worker_state[3] != 'terminate failed':
                    result = aws.terminate_machine(worker_state[2])
                    if result is not None:
                        self.client.delete(worker)
                    else:
                        worker_state[3] = 'terminate failed'
                        self.client.set(worker, pickle.dumps(worker_state))
