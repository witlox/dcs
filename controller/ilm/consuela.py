import json
import logging
from logging.config import dictConfig
import threading
import pickle
import redis

import aws
from settings import Settings


def terminate_worker(worker_id, instance, client):
    result = aws.terminate_machine(instance)
    if result is None or len(result) == 0:
        logging.error('could not remove worker %s, remove manually!' % instance)
    client.delete(worker_id)


class Consuela(threading.Thread):
    """ Manages the termination of machines """
    def __init__(self):
        with open('logging.json') as jl:
            dictConfig(json.load(jl))
        logging.info('Consuela: Starting.')
        threading.Thread.__init__(self)
        self.daemon = True
        self.settings = Settings()
        self.client = redis.Redis('db')
        self.job_pub_sub = self.client.pubsub()
        self.job_pub_sub.subscribe(['jobs'])

    def run(self):
        for item in self.job_pub_sub.listen():
            job_id = item['data']
            if job_id == 'KILL':
                self.job_pub_sub.unsubscribe()
                logging.info('Consuela: Stopping.')
                return
            #
            worker_id, worker = self.get_worker(job_id)
            if worker and self.client.exists(job_id):
                job = pickle.loads(self.client.get(job_id))
                if job.state == 'finished' and worker.instance is not None:
                    if not self.settings.recycle_workers:
                        logging.info('recycle workers off, %s finished, shutting down machine' % worker.instance)
                        terminate_worker(worker_id, worker.instance, self.client)
                    else:
                        if self.recycle_worker(job_id, job):
                            logging.info('going to recycle worker %s' % worker.instance)
                            worker.job_id = None
                            self.client.set(worker_id, pickle.dumps(worker))
                        else:
                            logging.info('no work left for %s, shutting down machine' % worker.instance)
                            terminate_worker(worker_id, worker.instance, self.client)
                elif job.state == 'failed' and worker.instance is not None:
                    logging.warning('%s finished with failure' % job_id)
                    if self.settings.auto_remove_failed and not self.settings.recycle_workers:
                        logging.info('auto-remove on failure enabled, trying to remove %s' % worker.instance)
                        terminate_worker(worker_id, worker.instance, self.client)
                    else:
                        logging.warning('auto-remove on failure not performed, manually remove %s!' % worker.instance)
                elif job.state == 'broken' and worker.instance is not None:
                    logging.info('Terminating worker with a broken job.')
                    terminate_worker(worker_id, worker.instance, self.client)
                    job.state = 'failed'
                    self.client.set(job_id, pickle.dumps(job))
            elif worker_id and worker and worker.instance:
                terminate_worker(worker_id, worker.instance, self.client)
            else:
                logging.debug('no worker found for %s' % job_id)

    def get_worker(self, job_id):
        for worker_id in [worker_key for worker_key in self.client.keys() if worker_key.startswith('jm-')]:  # Redis keys(pattern='*') does not filter at all.
            pickled_worker = self.client.get(worker_id)
            if pickled_worker is None:
                continue
            worker = pickle.loads(pickled_worker)
            if worker.job_id is not None and worker.job_id == job_id:
                return worker_id, worker
        return None, None

    def recycle_worker(self, job_id, job):
        if job.batch_id is None or not self.client.exists(job.batch_id):
            logging.info('could not find a "real" batch id for %s' % job.batch_id)
            return False
        batch = pickle.loads(self.client.get(job.batch_id))
        for batch_job_id in pickle.loads(batch.jobs):
            logging.debug('have job %s in batch %s' % (batch_job_id, job.batch_id))
            if batch_job_id != job_id:
                logging.debug('found other job in batch, checking state')
                if self.client.exists(batch_job_id):
                    batch_job = pickle.loads(self.client.get(batch_job_id))
                    logging.debug('state is %s (for %s)' % (batch_job.state, batch_job_id))
                    if batch_job.state == 'spawned' or batch_job.state == 'received' or batch_job.state == 'delayed':
                        return True
        return False
