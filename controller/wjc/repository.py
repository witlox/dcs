import json
from logging.config import dictConfig
import pickle
import logging
import shutil
import uuid
import redis
from batch import Batch


class JobRepository:
    def __init__(self):
        try:
            with open('logging.json') as jl:
                dictConfig(json.load(jl))
            self.client = redis.Redis('db')
        except Exception, e:
            logging.exception('Problem instantiating batch/job repository (%s)' % e)

    def get_all_jobs(self):
        result = []
        for job_id in [job_key for job_key in self.client.keys() if job_key.startswith('job-')]:  # Redis keys(pattern='*') does not filter at all.
            job = pickle.loads(self.client.get(job_id))
            result.append([job_id, job.batch_id, job.state, job.ami, job.instance_type])
        return result

    def get_job_state(self, job_id):
        if job_id.startswith('job-'):
            if self.client.exists(job_id):
                job = pickle.loads(self.client.get(job_id))
                if job is not None:
                    return job.state
                return 'job not found'
        return 'not a job'

    def set_job_state(self, job_id, state):
        if job_id.startswith('job-'):
            if self.client.exists(job_id):
                job = pickle.loads(self.client.get(job_id))
                if job is not None:
                    job.state = state
                    self.client.set(job_id, pickle.dumps(job))
                    self.client.publish('jobs', job_id)
                    return 'ok'
                return 'job not found'
        return 'not a job'

    def get_all_batches(self):
        result = []
        for batch_id in [batch_key for batch_key in self.client.keys() if batch_key.startswith('batch-')]:  # Redis keys(pattern='*') does not filter at all.
            batch = pickle.loads(self.client.get(batch_id))
            jobs = []
            if batch.jobs:
                jobs = pickle.loads(batch.jobs)
            result.append([batch_id, batch.state, batch.ami, batch.instance_type, batch.max_nodes, jobs])
        return result

    def execute_batch(self, max_nodes, ami, instance_type):
        batch_id = 'batch-%s' % uuid.uuid4()
        batch = Batch('received')
        batch.ami = ami
        batch.instance_type = instance_type
        batch.max_nodes = max_nodes
        self.client.set(batch_id, pickle.dumps(batch))
        self.client.publish('batches', batch_id)
        return batch_id

    def delete_batch(self, batch_id):
        if batch_id.startswith('batch-'):
            if self.client.exists(batch_id):
                for job_id in [job_key for job_key in self.client.keys() if job_key.startswith('job-')]:  # Redis keys(pattern='*') does not filter at all.
                    job = pickle.loads(self.client.get(job_id))
                    if job.batch_id == batch_id:
                        self.client.delete(job_id)
                        self.client.publish('jobs', job_id)
                try:
                    shutil.rmtree('/tmp/store/%s' % batch_id)
                except Exception, e:
                    raise 'could not delete %s (%s)' % (batch_id, e)
                finally:
                    return self.client.delete(batch_id)
        return 'not a batch'

    def get_batch_state(self, batch_id):
        if batch_id.startswith('batch-'):
            if self.client.exists(batch_id):
                batch = pickle.loads(self.client.get(batch_id))
                if batch is not None:
                    return batch.state
                return 'batch not found'
        return 'not a batch'

    def set_batch_state(self, batch_id, state):
        if batch_id.startswith('batch-'):
            if self.client.exists(batch_id):
                batch = pickle.loads(self.client.get(batch_id))
                batch.state = state
                self.client.set(batch_id, pickle.dumps(batch))
                self.client.publish('batches', batch_id)
                return 'ok'
        return 'not a batch'
