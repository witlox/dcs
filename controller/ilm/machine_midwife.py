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
        logging.info('checking for machine updates')
        for worker_id in self.client.keys('jm-*'):
            try:
                worker = pickle.loads(self.client.get(worker_id))
                job = pickle.loads(self.client.get(worker.job_id))
                if worker.reservation is not None and worker.instance is None and job.state == 'requested':
                    if datetime.now() - worker.request_time > timedelta(hours=1):
                        logging.warning('reservation %s has become stale, cleaning up' % worker.reservation)
                        self.client.set(worker_id, pickle.dumps(worker))
                        job.state = 'boot failed'
                        self.client.set(worker.job_id, pickle.dumps(job))
                        self.client.publish('jobs', worker.job_id)
                        continue
                aws_instance, ip_address = aws.my_booted_machine(worker.reservation)
                if aws_instance is not None:
                    logging.info('reservation %s booted to instance %s' % (worker.reservation, aws_instance))
                    worker.ip_address = ip_address
                    self.client.set(worker_id, pickle.dumps(worker))
                    job.state = 'booted'
                    self.client.set(worker.job_id, pickle.dumps(job))
                    self.client.publish('jobs', worker.job_id)
            except Exception:
                logging.exception('but not going to break our machine midwife')
