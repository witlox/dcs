from datetime import datetime, timedelta
import json
import logging
from logging.config import dictConfig
import threading
import pickle
from time import sleep
import redis
import aws
from settings import Settings
from worker import Worker


class MachineMidwife(threading.Thread):
    """ Manages the starting of machines """
    def __init__(self):
        with open('logging.json') as jl:
            dictConfig(json.load(jl))
        logging.info('starting machine midwife crisis')
        threading.Thread.__init__(self)
        self.daemon = True
        self.settings = Settings()
        if self.settings.max_instances >= aws.get_max_instances():
            logging.error('maximum instances setting larger than your AWS EC2 capacity, this can lead to an inconsistent state!')
        self.client = redis.Redis('db')
        self.job_pub_sub = self.client.pubsub()
        self.job_pub_sub.subscribe(['jobs'])
        self.apprentice = self.Apprentice(self.client)

    def run(self):
        self.apprentice.start()
        for item in self.job_pub_sub.listen():
            job_id = item['data']
            if job_id == 'KILL':
                self.apprentice.halt()
                self.job_pub_sub.unsubscribe()
                logging.info('sending midwife home')
                return
            if self.client.exists(job_id):
                job = pickle.loads(self.client.get(job_id))
                if job.state != 'received' and job.state != 'delayed':
                    continue
                job = pickle.loads(self.client.get(job_id))
                if job.state == 'received' or job.state == 'delayed':
                    recycled = False
                    for worker_id in self.client.keys('jm-*'):
                        existing_worker = pickle.loads(self.client.get(worker_id))
                        if existing_worker.batch_id == job.batch_id and existing_worker.job_id is None:
                            job.state = 'booted'
                            existing_worker.job_id = job_id
                            self.client.set(worker_id, pickle.dumps(existing_worker))
                            self.client.set(job_id, pickle.dumps(job))
                            self.client.publish('jobs', job_id)
                            recycled = True
                            break
                    if recycled:
                        continue
                    queue_full = self.choke_full()
                    # refresh job, the previous call can take some time and the state can become stale
                    if not self.client.exists(job_id):
                        continue
                    if not queue_full:
                        worker_id, reservation = aws.start_machine(job.ami, job.instance_type)
                        if worker_id:
                            job.state = 'requested'
                            worker = Worker(job_id, job.batch_id)
                            worker.request_time = datetime.now()
                            worker.reservation = reservation
                            self.client.set(worker_id, pickle.dumps(worker))
                        else:
                            job.state = 'failed'
                        self.client.set(job_id, pickle.dumps(job))
                        self.client.publish('jobs', job_id)
                    else:
                        job.state = 'delayed'
                        self.client.set(job_id, pickle.dumps(job))

    def choke_full(self):
        """Can we start more instances?"""
        instances = self.waldos()
        queue_full = False
        count = aws.active_instance_count()
        max_instances = aws.get_max_instances()
        max_storage = aws.get_storage_usage(instances)
        if count is not None and max_instances is not None and count >= max_instances:
            logging.warning('you are currently using your maximum AWS EC2 capacity (%d/%d)' % (count, max_instances))
            queue_full = True
        if len(instances) >= self.settings.max_instances:
            logging.warning('maximum amount of instances in use (%d of %d), delaying start of new worker' % (len(instances), self.settings.max_instances))
            queue_full = True
        if max_storage is not None and max_storage >= self.settings.max_storage:
            logging.warning('maximum amount of storage in use (%d of %d), delaying start of new worker' % (max_storage, self.settings.max_storage))
            queue_full = True
        return queue_full

    def waldos(self):
        instances = []
        for worker_id in self.client.keys('jm-*'):
            existing_worker = pickle.loads(self.client.get(worker_id))
            if existing_worker.instance is not None:
                instances.append(existing_worker.instance)
        return instances

    class Apprentice(threading.Thread):
        """ responsible for managing request delays, stale requests and booted state machines """
        def __init__(self, client):
            logging.debug('machine apprentice peeking')
            threading.Thread.__init__(self)
            self.daemon = True
            self.client = client
            self.settings = Settings()
            self.running = True

        def halt(self):
            self.running = False

        def run(self):
            while self.running:
                self.rise_and_shine()
                self.check_newborn()
                sleep(60)

        def rise_and_shine(self):
            logging.debug('checking for delays to signal')
            signaled = 0
            instances = []
            for worker_id in self.client.keys('jm-*'):
                existing_worker = pickle.loads(self.client.get(worker_id))
                if existing_worker.instance is not None:
                    instances.append(existing_worker.instance)
            for job_id in self.client.keys('job-*'):
                job = pickle.loads(self.client.get(job_id))
                if job.state == 'delayed':
                    if len(instances) + signaled < self.settings.max_instances:
                        self.client.publish('jobs', job_id)
                        signaled += 1

        def check_newborn(self):
            logging.debug('checking for machine updates')
            for worker_id in self.client.keys('jm-*'):
                worker = pickle.loads(self.client.get(worker_id))
                if self.client.exists(worker.job_id):
                    job = pickle.loads(self.client.get(worker.job_id))
                    if worker.reservation is not None and worker.instance is None and job.state == 'requested':
                        if datetime.now() - worker.request_time > timedelta(minutes=int(self.settings.aws_req_max_wait)):
                            logging.warning('reservation %s has become stale, restarting' % worker.reservation)
                            job.state = 'received'
                            self.client.set(worker.job_id, pickle.dumps(job))
                            self.client.publish('jobs', worker.job_id)
                            self.client.delete(worker_id)
                            continue
                        aws_instance, ip_address = aws.my_booted_machine(worker.reservation)
                        if aws_instance is not None and ip_address is not None:
                            logging.info('reservation %s booted to instance %s' % (worker.reservation, aws_instance))
                            worker.instance = aws_instance
                            worker.ip_address = ip_address
                            self.client.set(worker_id, pickle.dumps(worker))
                            job.state = 'booted'
                            self.client.set(worker.job_id, pickle.dumps(job))
                            self.client.publish('jobs', worker.job_id)
