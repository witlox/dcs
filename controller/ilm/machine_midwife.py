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
        logging.info('MachineMidwife: Starting.')
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
                logging.info('MachineMidwife: Stopping.')
                return
            #
            queue_full = self.choke_full()
            #
            logging.debug('MachineMidwife: Redis signals for job: ' + job_id)
            if not self.client.exists(job_id):
                logging.warning('MachineMidwife: Redis signaled for non-existing job: ' + job_id)
                continue
            job = pickle.loads(self.client.get(job_id))
            logging.debug('MachineMidwife: Job %s has state %s' % (job_id, job.state))
            if job.state != 'received' and job.state != 'delayed':
                continue
            # Recycle
            recycled = False
            for worker_id in [worker_key for worker_key in self.client.keys() if worker_key.startswith('jm-')]:  # Redis keys(pattern='*') does not filter at all.
                if not self.client.exists(worker_id):
                    continue
                existing_worker = pickle.loads(self.client.get(worker_id))
                if existing_worker.batch_id == job.batch_id and existing_worker.job_id is None:
                    logging.info('MachineMidwife: Recycling worker %s for job %s of batch %s.' % (worker_id, job_id, job.batch_id))
                    job.state = 'booted'
                    existing_worker.job_id = job_id
                    self.client.set(worker_id, pickle.dumps(existing_worker))
                    self.client.set(job_id, pickle.dumps(job))
                    self.client.publish('jobs', job_id)
                    recycled = True
                    break
            if recycled:
                continue
            # New machine
            if not queue_full:
                worker_id, reservation = aws.start_machine(job.ami, job.instance_type)
                if worker_id is not None:
                    logging.info('MachineMidwife: Started new worker for job %s of batch %s.' % (job_id, job.batch_id))
                    job.state = 'requested'
                    worker = Worker(job_id, job.batch_id)
                    worker.request_time = datetime.now()
                    worker.reservation = reservation
                    self.client.set(worker_id, pickle.dumps(worker))
                    self.client.set(job_id, pickle.dumps(job))
                    self.client.publish('jobs', job_id)
                else:
                    logging.warning('MachineMidwife: AWS failed to start a new machine.')
                    job.state = 'delayed'
                    self.client.set(job_id, pickle.dumps(job))
            else:
                job.state = 'delayed'
                self.client.set(job_id, pickle.dumps(job))

    def choke_full(self):
        """Can we start more instances?"""
        instances = self.waldos()
        count = aws.active_instance_count()
        max_instances = aws.get_max_instances()
        max_storage = aws.get_storage_usage(instances)
        if count is not None and max_instances is not None and count >= max_instances:
            logging.debug('currently using your maximum AWS EC2 capacity (%d/%d)' % (count, max_instances))
            return True
        if len(instances) >= self.settings.max_instances:
            logging.warning('maximum amount of instances in use (%d of %d)' % (len(instances), self.settings.max_instances))
            return True
        if max_storage is not None and max_storage >= self.settings.max_storage:
            logging.warning('maximum amount of storage in use (%d of %d)' % (max_storage, self.settings.max_storage))
            return True
        return False

    def waldos(self):
        instances = []
        for worker_id in [worker_key for worker_key in self.client.keys() if worker_key.startswith('jm-')]:  # Redis keys(pattern='*') does not filter at all.
            pickled_worker = self.client.get(worker_id)
            if pickled_worker is None:
                continue
            existing_worker = pickle.loads(pickled_worker)
            if existing_worker.instance is not None:
                instances.append(existing_worker.instance)
        return instances

    class Apprentice(threading.Thread):
        """ responsible for managing request delays, stale requests and booted state machines """
        def __init__(self, client):
            threading.Thread.__init__(self)
            self.daemon = True
            self.client = client
            self.settings = Settings()
            self.running = True
            logging.info('MachineMidwife apprentice: Starting.')

        def halt(self):
            if not self.running:
                logging.info('MachineMidwife apprentice: Stopping.')
                self.running = False

        def run(self):
            while self.running:
                self.rise_and_shine()
                self.check_newborn()
                sleep(300)

        def rise_and_shine(self):
            logging.debug('MachineMidwife apprentice: Checking for delayed jobs to signal.')
            signaled = 0
            instances = []
            for worker_id in [worker_key for worker_key in self.client.keys() if worker_key.startswith('jm-')]:  # Redis keys(pattern='*') does not filter at all.
                pickled_worker = self.client.get(worker_id)
                if pickled_worker is None:
                    continue
                existing_worker = pickle.loads(pickled_worker)
                if existing_worker.instance is not None:
                    instances.append(existing_worker.instance)
            for job_id in [job_key for job_key in self.client.keys() if job_key.startswith('job-')]:  # Redis keys(pattern='*') does not filter at all.
                pickled_job = self.client.get(job_id)
                if pickled_job is None:
                    continue
                job = pickle.loads(pickled_job)
                if job.state == 'delayed':
                    # We could additionally check on the batch's worker quotum.
                    if len(instances) + signaled < self.settings.max_instances:
                        self.client.publish('jobs', job_id)
                        signaled += 1

        def check_newborn(self):
            logging.debug('MachineMidwife apprentice: Checking for machine updates.')
            for worker_id in [worker_key for worker_key in self.client.keys() if worker_key.startswith('jm-')]:  # Redis keys(pattern='*') does not filter at all.
                pickled_worker = self.client.get(worker_id)
                if pickled_worker is None:
                    continue
                worker = pickle.loads(pickled_worker)
                pickled_job = self.client.get(worker.job_id)
                if pickled_job is None:
                    continue
                job = pickle.loads(pickled_job)
                if worker.reservation is not None and worker.instance is None and job.state == 'requested':
                    if datetime.now() - worker.request_time > timedelta(minutes=int(self.settings.aws_req_max_wait)):
                        logging.error('MachineMidwife apprentice: Reservation %s of worker %s has become stale, terminate machine manually.' % (worker.reservation, worker_id))
                        self.client.delete(worker_id)
                        job.state = 'received'
                        self.client.set(worker.job_id, pickle.dumps(job))
                        self.client.publish('jobs', worker.job_id)
                        continue
                    aws_instance, ip_address = aws.my_booted_machine(worker.reservation)
                    if aws_instance is not None and ip_address is not None:
                        logging.info('MachineMidwife apprentice: Reservation %s booted to instance %s' % (worker.reservation, aws_instance))
                        worker.instance = aws_instance
                        worker.ip_address = ip_address
                        self.client.set(worker_id, pickle.dumps(worker))
                        job.state = 'booted'
                        self.client.set(worker.job_id, pickle.dumps(job))
                        self.client.publish('jobs', worker.job_id)
