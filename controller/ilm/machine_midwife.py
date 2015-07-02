from datetime import datetime, timedelta
import logging
import aws
import pickle
from threading import Timer


class MachineMidwife:
    def __init__(self, client):
        self.client = client
        logging.info('starting machine midwife crisis')
        self.timer = Timer(60, self.check_newborn)
        self.timer.start()

    def check_newborn(self):
        for key in self.client.keys('jm-*'):
            job_id, reservation, instance, state, request_timestamp = pickle.loads(self.client.get(key))
            if instance is None and state == 'requested':
                if datetime.now() - request_timestamp > timedelta(hours=1):
                    self.client.set(key, pickle.dumps(job_id, reservation, aws_instance, 'request failed'))
                    job = pickle.loads(self.client.get(job_id))
                    job[2] = 'boot failed'
                    self.client.set(job_id, pickle.dumps(job))
                    self.client.publish('jobs', job_id)
                    continue
                aws_instance, ip_address = aws.my_booted_machine(reservation)
                if aws_instance:
                    self.client.set(key, pickle.dumps(job_id, reservation, aws_instance, 'booted', ip_address))
                    job = pickle.loads(self.client.get(job_id))
                    job[2] = 'booted'
                    self.client.set(job_id, pickle.dumps(job))
                    self.client.publish('jobs', job_id)
