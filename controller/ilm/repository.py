from datetime import datetime
import json
import pickle
import logging
import threading
import redis
import aws
from logging.config import dictConfig
from machine_midwife import MachineMidwife
from worker import Worker

with open('logging.json') as jl:
    dictConfig(json.load(jl))

class AmiRepository(threading.Thread):
    def __init__(self):
        try:
            threading.Thread.__init__(self)
            self.daemon = True
            self.client = redis.Redis('db')
            self.pubsub = self.client.pubsub()
            self.pubsub.subscribe(['jobs'])
            self.midwife = MachineMidwife(self.client)
            self.midwife.start()
            self.start()
        except Exception:
            logging.exception('Cannot connect with the database server')

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

    def get_all_workers(self):
        result = []
        for key in self.client.keys('jm-*'):
            worker = pickle.loads(self.client.get(key))
            result.append([key, worker.job_id, worker.reservation, worker.instance, worker.request_time, worker.ip_address])
        return result

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
            if job.state == 'received':
                worker_id, reservation = aws.start_machine(job.ami, job.instance_type)
                if worker_id:
                    job.state = 'requested'
                    worker = Worker(job_id)
                    worker.request_time = datetime.now()
                    worker.reservation = reservation
                    self.client.set(worker_id, pickle.dumps(worker))
                else:
                    job.state = 'ami request failed'
                self.client.set(job_id, pickle.dumps(job))
                self.client.publish('jobs', job_id)
        else:
            logging.info('removing worker for job %s' % job_id)
            for worker_id in self.client.keys('jm-*'):
                worker = pickle.loads(self.client.get(worker_id))
                if worker.job_id == job_id and worker.instance is not None:
                    result = aws.terminate_machine(worker.instance)
                    if result is None:
                        logging.error('Could not remove worker %s, remove manually!' % worker.instance)
                    self.client.delete(worker_id)
