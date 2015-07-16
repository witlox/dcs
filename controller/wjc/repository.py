import json
from logging.config import dictConfig
import pickle
import logging
import uuid
import redis
from job_midwife import JobMidwife
from job import Job

with open('logging.json') as jl:
    dictConfig(json.load(jl))

class JobRepository:
    def __init__(self):
        try:
            self.client = redis.Redis('db')
            self.midwife = JobMidwife(self.client)
        except Exception, e:
            logging.error("Cannot connect with the database server: " + e)
            raise

    def get_all_jobs(self):
        result = []
        for job_key in self.client.keys('job-*'):
            job = pickle.loads(self.client.get(job_key))
            result.append([job_key, job.state, job.ami, job.instance_type])
        return result

    def insert_job(self, ami, instance_type):
        job_id = 'job-%s' % uuid.uuid4()
        job = Job('received')
        job.ami = ami
        job.instance_type = instance_type
        self.client.set(job_id, pickle.dumps(job))
        self.client.publish('jobs', job_id)
        return job_id

    def delete_job(self, job_id):
        result = self.client.delete(job_id)
        self.client.publish('jobs', job_id)
        return result

    def get_job_state(self, job_id):
        job = pickle.loads(self.client.get(job_id))
        if job is not None:
            return job.state
        return 'job not found'

    def set_job_state(self, job_id, state):
        job = pickle.loads(self.client.get(job_id))
        if job is not None:
            job.state = state
            self.client.set(job_id, pickle.dumps(job))
            self.client.publish('jobs', job_id)
            return 'ok'
        return 'job not found'