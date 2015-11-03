import json
import logging
from logging.config import dictConfig
import os
import pickle
import threading
from time import sleep
import redis
import shutil

from settings import Settings
from job import Job


class BatchMidwife(threading.Thread):
    def __init__(self):
        with open('logging.json') as jl:
            dictConfig(json.load(jl))
        logging.debug('BatchMidwife: Starting.')
        threading.Thread.__init__(self)
        self.daemon = True
        self.headers = {'User-agent': 'dcs_ilm/1.0'}
        self.settings = Settings()
        self.client = redis.Redis('db')
        self.batch_pub_sub = self.client.pubsub()
        self.batch_pub_sub.subscribe(['batches'])
        self.apprentice = self.Apprentice(self.client)

    def run(self):
        self.apprentice.start()
        for item in self.batch_pub_sub.listen():
            if item['data'] == 'KILL':
                self.apprentice.halt()
                self.batch_pub_sub.unsubscribe()
                logging.debug('BatchMidwife: Stopping.')
                break
            else:
                batch_id = item['data']
                logging.debug('BatchMidwife: Redis signals for batch: ' + batch_id)
                if not self.client.exists(batch_id):
                    logging.warning('BatchMidwife: Redis signaled for non-existing batch: ' + batch_id)
                    continue
                batch = pickle.loads(self.client.get(batch_id))
                logging.debug('BatchMidwife: Batch %s has state %s' % (batch_id, batch.state))
                if batch.state != 'uploaded':
                    continue
                if batch.jobs is None:
                    logging.info('BatchMidwife: Reading jobs from uploaded batch: ' + batch_id)
                    debutantes = os.listdir('/tmp/store/%s' % batch_id)
                    carousers = []
                    for debutante in debutantes:
                        bumboo = 1
                        scallywag = debutante + "_" + str(bumboo)
                        while scallywag in self.client.keys():
                            bumboo += 1
                            scallywag = scallywag[:-(len(str(bumboo - 1)))] + str(bumboo)
                        if scallywag != debutante:
                            shutil.move('/tmp/store/%s/%s' % (batch_id, debutante),
                                        '/tmp/store/%s/%s' % (batch_id, scallywag))
                        carousers.append(scallywag)
                    batch.jobs = pickle.dumps(carousers)
                    self.client.set(batch_id, pickle.dumps(batch))
                    for job_id in carousers:
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
            threading.Thread.__init__(self)
            self.daemon = True
            self.client = client
            self.running = True

        def halt(self):
            if not self.running:
                logging.debug('Apprentice: Stopping.')
                self.running = False

        def run(self):
            loop_count = 0
            while self.running:
                for batch_id in self.client.keys('batch-*'):
                    if batch_id == 'KILL':
                        self.halt()
                        continue
                    pickled_batch = self.client.get(batch_id)
                    if pickled_batch is None:
                        continue  # self.client.keys('batch-*') is stale
                    batch = pickle.loads(pickled_batch)
                    if batch.state != 'running':
                        continue
                    finished = 0
                    current = 0
                    pending = 0
                    failed = 0
                    total = 0
                    stale_jobs = False
                    for job_id in pickle.loads(batch.jobs):
                        pickled_job = self.client.get(job_id)
                        if pickled_job is None:
                            stale_jobs = True
                            break  # batch.jobs is stale
                        job = pickle.loads(pickled_job)
                        if job.state == 'received' or job.state == 'requested' or job.state == 'booted' or \
                                        job.state == 'running' or job.state == 'run_succeeded' or job.state == 'run_failed':
                            current += 1
                        elif job.state == 'delayed' or job.state == 'spawned':
                            pending += 1
                        elif job.state == 'finished':
                            finished += 1
                        elif job.state == 'failed':
                            failed += 1
                        total += 1
                    if stale_jobs:
                        continue  # Don't trust the status counters.
                    if loop_count % 10 == 0:
                        logging.info("currently servicing %d jobs and finished %d jobs of %d total jobs in %s" % (
                            current, finished + failed, total, batch_id))
                    if finished + failed == total:
                        logging.info('all jobs for batch %s have been completed, (%d failures)' % (batch_id, failed))
                        batch.state = 'finished'
                        self.client.set(batch_id, pickle.dumps(batch))
                        continue
                    for job_id in pickle.loads(batch.jobs):
                        pickled_job = self.client.get(job_id)
                        if pickled_job is None:
                            continue  # batch.jobs is stale
                        job = pickle.loads(pickled_job)
                        if job.state == 'spawned' and current < batch.max_nodes:
                            logging.info('detected empty slot (%d/%d) for %s, creating job' % (
                                batch.max_nodes - current, batch.max_nodes, batch_id))
                            job.state = 'received'
                            self.client.set(job_id, pickle.dumps(job))
                            self.client.publish('jobs', job_id)
                            current += 1
                loop_count += 1
                if self.running:
                    sleep(60)
