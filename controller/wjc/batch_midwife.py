import json
import logging
from logging.config import dictConfig
import os
import pickle
import threading
from time import sleep
import redis

from settings import Settings
from job import Job


class BatchMidwife(threading.Thread):
    def __init__(self):
        with open('logging.json') as jl:
            dictConfig(json.load(jl))
        logging.info('starting batch midwife crisis')
        threading.Thread.__init__(self)
        self.daemon = True
        self.headers = {'User-agent': 'dcs_ilm/1.0'}
        self.settings = Settings()
        self.client = redis.Redis('db')
        self.job_pub_sub = self.client.pubsub()
        self.job_pub_sub.subscribe(['batches'])
        self.apprentice = self.Apprentice(self.client)

    def run(self):
        self.apprentice.start()
        for item in self.job_pub_sub.listen():
            if item['data'] == 'KILL':
                self.apprentice.halt()
                self.job_pub_sub.unsubscribe()
                logging.info('sending batch midwife home')
                break
            else:
                batch_id = item['data']
                logging.debug(batch_id)
                if not self.client.exists(batch_id):
                    continue
                batch = pickle.loads(self.client.get(batch_id))
                logging.info('%s has state %s' % (batch_id, batch.state))
                if batch.state != 'uploaded':
                    continue
                if not batch.jobs:
                    unique_jobs = [ajob+batch_id for ajob in os.listdir('/tmp/store/%s' % batch_id)]
                    batch.jobs = pickle.dumps(unique_jobs)
                    self.client.set(batch_id, pickle.dumps(batch))
                    for job_id in pickle.loads(batch.jobs):
                        job = Job('spawned', batch_id)
                        job.ami = batch.ami
                        job.instance_type = batch.instance_type
                        self.client.set(job_id, pickle.dumps(job))
                        self.client.publish('jobs', job_id)
                    batch.state = 'running'
                    self.client.set(batch_id, pickle.dumps(batch))

    class Apprentice(threading.Thread):
        """ responsible for managing running batch state """

        def __init__(self, client):
            logging.debug('batch apprentice peeking')
            threading.Thread.__init__(self)
            self.daemon = True
            self.client = client
            self.running = True

        def halt(self):
            self.running = False

        def run(self):
            while self.running:
                for batch_key in self.client.keys('batch-*'):
                    batch = pickle.loads(self.client.get(batch_key))
                    if batch.state != 'running':
                        continue
                    finished = 0
                    current = 0
                    failed = 0
                    for job_id in pickle.loads(batch.jobs):
                        if self.client.exists(job_id):
                            job = pickle.loads(self.client.get(job_id))
                            if job.state == 'received' or job.state == 'requested' or \
                                    job.state == 'delayed' or job.state == 'booted' or \
                                    job.state == 'running' or job.state == 'run_succeeded' or \
                                    job.state == 'run_failed':
                                current += 1
                            elif job.state == 'finished':
                                finished += 1
                            elif job.state == 'failed':
                                failed += 1
                    logging.info("currently servicing %d jobs and finished %d jobs of %d total jobs in %s" % (current, finished + failed, len(pickle.loads(batch.jobs)), batch_key))
                    if finished + failed == len(pickle.loads(batch.jobs)):
                        logging.info('all batch jobs have been completed, (%d failures)' % failed)
                        batch.state = 'finished'
                        self.client.set(batch_key, pickle.dumps(batch))
                        continue
                    for job_id in pickle.loads(batch.jobs):
                        if self.client.exists(job_id):
                            job = pickle.loads(self.client.get(job_id))
                            if job.state == 'spawned' and current < batch.max_nodes:
                                logging.info('detected empty slot (%d/%d) for %s, creating job' % (batch.max_nodes - current, batch.max_nodes, batch_key))
                                job.state = 'received'
                                self.client.set(job_id, pickle.dumps(job))
                                self.client.publish('jobs', job_id)
                                current += 1
                sleep(60)
