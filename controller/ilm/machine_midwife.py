from datetime import datetime, timedelta
import logging
import threading
from time import sleep
import pickle
import paramiko
import aws
from settings import Settings
from ftp_util import sync


def terminate_worker(worker):
    result = aws.terminate_machine(worker.instance)
    if result is None:
        logging.error('Could not remove worker %s, remove manually!' % worker.instance)


class MachineMidwife(threading.Thread):
    def __init__(self, client):
        logging.info('starting machine midwife crisis')
        threading.Thread.__init__(self)
        self.daemon = True
        self.settings = Settings()
        self.client = client
        self.running = True

    def halt(self):
        self.running = False

    def run(self):
        while self.running:
            self.poky_pokey()
            self.check_newborn()
            sleep(60)
        logging.info('sending midwife home')

    def check_newborn(self):
        logging.debug('checking for machine updates')
        for worker_id in self.client.keys('jm-*'):
            try:
                worker = pickle.loads(self.client.get(worker_id))
                if not self.client.exists(worker.batch_id):
                    if self.settings.auto_remove_failed:
                        logging.info('found worker disconnected from batch and auto-remove on failure enabled, trying to remove %s' % worker.instance)
                        terminate_worker(worker)
                    else:
                        logging.warning('found worker disconnected from batch but auto-remove on failure disabled, manually remove %s!' % worker.instance)
                    self.client.delete(worker_id)
                    continue
                if not self.client.exists(worker.job_id):
                    continue
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
                    if aws_instance is not None:
                        logging.info('reservation %s booted to instance %s' % (worker.reservation, aws_instance))
                        worker.instance = aws_instance
                        worker.ip_address = ip_address
                        self.client.set(worker_id, pickle.dumps(worker))
                        job.state = 'booted'
                        self.client.set(worker.job_id, pickle.dumps(job))
                        self.client.publish('jobs', worker.job_id)
                elif worker.instance is not None and job.state == 'finished':
                    logging.info('%s finished with success' % worker.job_id)
                    self.pull(job.ami, worker.batch_id, worker.job_id, worker.ip_address, self.settings.recycle_workers)
                    if not self.settings.recycle_workers:
                        logging.info('recycle workers off, %s finished, shutting down machine' % worker.instance)
                        terminate_worker(worker)
                        self.client.delete(worker_id)
                    else:
                        for job_id in self.client.keys('job-*'):
                            job = pickle.loads(self.client.get(job_id))
                            if job.batch_id == worker.batch_id:
                                if job.state == 'spawned':
                                    worker.job_id = None
                                    self.client.set(worker_id, pickle.dumps(worker))
                                    break
                        if worker.job_id is not None:
                            terminate_worker(worker)
                            self.client.delete(worker_id)
                elif worker.instance is not None and job.state == 'failed':
                    logging.warning('%s finished with failure' % worker.job_id)
                    self.pull(job.ami, worker.batch_id, worker.job_id, worker.ip_address, False, True)
                    if self.settings.auto_remove_failed:
                        logging.info('auto-remove on failure enabled, trying to remove %s' % worker.instance)
                        terminate_worker(worker)
                    else:
                        logging.warning('auto-remove on failure disabled, manually remove %s!' % worker.instance)
                    self.client.delete(worker_id)
            except Exception, e:
                logging.exception('but not going to break our machine midwife (%s)' % e)

    def poky_pokey(self):
        logging.debug('clean up lingering machines')
        for batch_id in self.client.keys('batch-*'):
            try:
                batch = pickle.loads(self.client.get(batch_id))
                are_we_there_yet = True
                for job_id in batch.jobs:
                    if self.client.exists(job_id):
                        job = pickle.loads(self.client.get(job_id))
                        if job.state == 'spawned':
                            are_we_there_yet = False
                            break
                if are_we_there_yet:
                    for worker_id in self.client.keys('jm-*'):
                        worker = pickle.loads(self.client.get(worker_id))
                        if worker.job_id is None:
                            terminate_worker(worker)
                            self.client.delete(worker_id)
            except Exception, e:
                logging.exception('something failed (%s)' % e)

    def pull(self, ami, batch_id, job_id, ip_address, clean=True, failed=False):
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            username, key_file = pickle.loads(self.client.get(ami))
            logging.info('establishing connection to %s using user %s' % (ip_address, username))
            with open('%s.key' % job_id, 'wb') as hairy:
                hairy.write(key_file)
            ssh.connect(hostname=ip_address, username=username, key_filename='%s.key' % job_id)
            with ssh.open_sftp() as sftp:
                destination = '/tmp/store/%s/%s' % (batch_id, job_id)
                if failed:
                    destination += '_failed'
                sync(sftp, job_id, destination)
            if clean:
                ssh.exec_command('rm -rf %s' % job_id)
                ssh.exec_command('rm -f %s.sh' % job_id)
            logging.info('transferred results for %s, saved to %s' % (job_id, destination))
