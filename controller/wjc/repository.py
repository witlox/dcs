import json
from logging.config import dictConfig
import pickle
import logging
import uuid
import redis

dictConfig(json.load('logging.json'))

class JobRepository:
    def __init__(self):
        try:
            self.client = redis.Redis('db')
        except Exception, e:
            logging.error("Cannot connect with the database server: " + e)
            raise

    def get_all_jobs(self):
        return self.client.keys('job-*')

    def insert_job(self, ami, instance_type):
        job_id = 'job-%s' % uuid.uuid4()
        self.client.set(job_id, pickle.dumps([ami, instance_type, 'received']))
        self.client.publish('jobs', job_id)
        return job_id

    def delete_job(self, job_id):
        result = self.client.delete(job_id)
        self.client.publish('jobs', job_id)
        return result

    def get_job_state(self, job_id):
        job = pickle.loads(self.client.get(job_id))
        if job is not None:
            return job[2]
        return 'job not found'

    def set_job_state(self, job_id, state):
        job = pickle.loads(self.client.get(job_id))
        if job is not None:
            job[2] = state
            self.client.set(job_id, pickle.dumps(job))
            self.client.publish('jobs', job_id)
        return 'job not found'
