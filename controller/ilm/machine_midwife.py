from datetime import datetime, timedelta
import logging
import threading
from time import sleep
import aws
import pickle
from settings import Settings


class MachineMidwife(threading.Thread):

    logger = logging.getLogger(__name__)

    def __init__(self, client):
        self.logger.info('starting machine midwife crisis')
        threading.Thread.__init__(self)
        self.daemon = True
        self.settings = Settings()
        self.client = client
        self.running = True

    def halt(self):
        self.running = False

    def run(self):
        while self.running:
            self.check_newborn()
            sleep(60)
        self.logger.info('sending midwife home')

    def check_newborn(self):
        self.logger.info('checking for machine updates')
        for worker_id in self.client.keys('jm-*'):
            try:
                worker = pickle.loads(self.client.get(worker_id))
                job = pickle.loads(self.client.get(worker.job_id))
                if worker.reservation is not None and worker.instance is None and job.state == 'requested':
                    if datetime.now() - worker.request_time > timedelta(hours=1):
                        self.logger.warning('reservation %s has become stale, cleaning up' % worker.reservation)
                        self.client.set(worker_id, pickle.dumps(worker))
                        job.state = 'boot failed'
                        self.client.set(worker.job_id, pickle.dumps(job))
                        self.client.publish('jobs', worker.job_id)
                        continue
                    aws_instance, ip_address = aws.my_booted_machine(worker.reservation)
                    if aws_instance is not None:
                        self.logger.info('reservation %s booted to instance %s' % (worker.reservation, aws_instance))
                        worker.instance = aws_instance
                        worker.ip_address = ip_address
                        self.client.set(worker_id, pickle.dumps(worker))
                        job.state = 'booted'
                        self.client.set(worker.job_id, pickle.dumps(job))
                        self.client.publish('jobs', worker.job_id)
                elif worker.instance is not None and job.state == 'finished':
                    self.logger.info('%s finished, shutting down machine' % worker.instance)
                    result = aws.terminate_machine(worker.instance)
                    if result is None:
                        self.logger.error('Could not remove worker %s, remove manually!' % worker.instance)
                elif worker.instance is not None and job.state == 'failed':
                    if self.settings.aws_auto_remove_failed:
                        self.logger.info('autoremove on failure enabled, trying to remove %s' % worker.instance)
                        result = aws.terminate_machine(worker.instance)
                        if result is None:
                            self.logger.error('Could not remove worker %s, remove manually!' % worker.instance)
                    else:
                        self.logger.warning('autoremove on failure disabled, manually remove %s!' % worker.instance)
            except Exception:
                self.logger.exception('but not going to break our machine midwife')
