from datetime import datetime, timedelta
import logging
import threading
from time import sleep
import pickle
import paramiko
import requests
import aws
from settings import Settings


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
            self.check_newborn()
            sleep(60)
        logging.info('sending midwife home')

    def check_newborn(self):
        logging.debug('checking for machine updates')
        for worker_id in self.client.keys('jm-*'):
            try:
                worker = pickle.loads(self.client.get(worker_id))
                job = pickle.loads(self.client.get(worker.job_id))
                if worker.reservation is not None and worker.instance is None and job.state == 'requested':
                    if datetime.now() - worker.request_time > timedelta(minutes=15):
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
                    logging.info('%s finished, shutting down machine' % worker.instance)
                    result = aws.terminate_machine(worker.instance)
                    if result is None:
                        logging.error('Could not remove worker %s, remove manually!' % worker.instance)
                    self.client.delete(worker_id)
                elif worker.instance is not None and job.state == 'failed':
                    r = requests.get('http://%s/store/files/' % self.settings.web)
                    job_zip = '%s.zip' % worker.job_id
                    if job_zip not in r.content:
                        try:
                            logging.warning('could not find %s output in store, trying to rescue output' % worker.job_id)
                            ssh = paramiko.SSHClient()
                            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            username, key_file = pickle.loads(self.client.get(job.ami))
                            with open('%s.key' % worker.job_id, 'wb') as hairy:
                                hairy.write(key_file)
                            logging.info('establishing connection to %s using user %s' % (worker.ip_address, username))
                            ssh.connect(hostname=worker.ip_address, username=username, key_filename='%s.key' % worker.job_id)
                            sftp = ssh.open_sftp()
                            dest = '%s/%s' % (self.settings.recovery_path, job_zip)
                            sftp.get(job_zip, dest)
                            sftp.close()
                            ssh.close()
                            logging.info('rescued results for %s, saved to %s' % (worker.job_id, dest))
                        except Exception, e:
                            logging.exception('could not recover results for %s (%s)' % (worker.job_id, e.message))
                    if self.settings.aws_auto_remove_failed:
                        logging.info('autoremove on failure enabled, trying to remove %s' % worker.instance)
                        result = aws.terminate_machine(worker.instance)
                        if result is None:
                            logging.error('Could not remove worker %s, remove manually!' % worker.instance)
                    else:
                        logging.warning('autoremove on failure disabled, manually remove %s!' % worker.instance)
                    self.client.delete(worker_id)
            except Exception:
                logging.exception('but not going to break our machine midwife')
