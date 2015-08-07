import json
import logging
import os
import pickle
import requests
import stat
import threading
from time import sleep

import paramiko

from settings import Settings
from job import Job

from ftp_util import sync

class JobMidwife(threading.Thread):
    def __init__(self, client):
        logging.info('starting job midwife crisis')
        threading.Thread.__init__(self)
        self.daemon = True
        self.settings = Settings()
        self.client = client
        self.running = True
        self.headers = {'User-agent': 'dcs_ilm/1.0'}

    def halt(self):
        self.running = False

    def run(self):
        while self.running:
            self.check_newborn()
            sleep(60)
        logging.info('sending midwife home')

    def check_newborn(self):
        self.sense_blubberies()
        logging.debug('checking for job updates')
        for job_key in self.client.keys('job-*'):
            try:
                job = pickle.loads(self.client.get(job_key))
                if job.state != 'booted':
                    continue
                worker = None
                for worker_key in self.client.keys('jm-*'):
                    temp_worker = pickle.loads(self.client.get(worker_key))
                    if temp_worker.job_id == job_key:
                        worker = temp_worker
                if worker.ip_address is None:
                    raise Exception('Could not determine IP address for worker/job %s' % job_key)
                # check if state is ok
                ami_status = requests.get('http://%s/ilm/ami/%s/status' % (self.settings.web, worker.instance), headers=self.headers)
                if 'status:ok' not in ami_status.content.lower():
                    logging.info('AMI (%s) status (%s) NOK, waiting...' % (worker.instance, ami_status.content))
                    continue
                logging.info('found job to transmit to worker %s, preparing script' % job_key)
                ramon = None
                with open('ramon.py', 'r') as r:
                    ramon = r.read()
                ramon = ramon.replace('[web]', self.settings.web)
                ramon = ramon.replace('[elk]', self.settings.elk)
                ramon = ramon.replace('[uuid]', job_key)
                ramon_file = '%s.sh' % job_key
                with open(ramon_file, 'w') as smooth:
                    smooth.writelines(ramon)
                st_fn = os.stat(ramon_file)
                os.chmod(ramon_file, st_fn.st_mode | stat.S_IEXEC)
                logging.info('script %s prepared' % ramon_file)
                # fish ami
                ami_req = 'http://%s/ilm/ami/%s' % (self.settings.web, job.ami)
                logging.info('retrieving AMI settings from %s' % ami_req)
                r_ami = requests.get(ami_req, headers=self.headers)
                data = pickle.loads(json.loads(r_ami.content))
                username = data[0]
                key_file = data[1]
                with paramiko.SSHClient() as ssh:
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    logging.info('establishing connection to %s using user %s' % (worker.ip_address, username))
                    with open('%s.key' % job_key, 'wb') as hairy:
                        hairy.write(key_file)
                    ssh.connect(hostname=worker.ip_address, username=username, key_filename='%s.key' % job_key)
                    with ssh.open_sftp() as sftp:
                        luke = '/tmp/store/%s/%s' % (job.batch, job_key)
                        sync(sftp, luke, job_key, download=False)
                        sftp.put(ramon_file, ramon_file)
                        ssh.exec_command('chmod +x %s' % ramon_file)
                        start = 'virtualenv venv\nsource venv/bin/activate\npip install python-logstash requests\nnohup ./%s  > /dev/null 2>&1 &\n' % ramon_file
                        logging.info('calling remote start with %s' % start)
                        _, out, err = ssh.exec_command(start)
                        output = out.readlines()
                        error = err.readlines()
                        if output:
                            logging.info('%s output: %s' % (job_key, output))
                        if error:
                            logging.error('%s error: %s' % (job_key, error))
                            requests.post('http://%s/wjc/jobs/%s/state/failed' % (self.settings.web, job_key), headers=self.headers)
                os.remove(ramon_file)
            except Exception, e:
                logging.exception('failure in %s (%s), continuing...' % (job_key, e))

    def sense_blubberies(self):
        for batch_key in self.client.keys('batch-*'):
            try:
                batch = pickle.loads(self.client.get(batch_key))
                if batch.state == 'uploaded':
                    if len(batch.jobs) == 0:
                        batch.jobs.extend(os.listdir('/tmp/store/%s' % batch_key))
                        self.client.set(batch_key, pickle.dumps(batch))
                        for job_id in batch.jobs:
                            job = Job('spawned', batch_key)
                            job.ami = batch.ami
                            job.instance_type = batch.instance_type
                            self.client.set(job_id, pickle.dumps(job))
                            self.client.publish('jobs', job_id)
                    finished = 0
                    current = 0
                    for job_id in batch.jobs:
                        if self.client.exists(job_id):
                            job = pickle.loads(self.client.get(job_id))
                            if job.state == 'running':
                                current += 1
                            elif job.state == 'finished' and job.state != 'failed':
                                finished += 1
                    logging.info("currently running %d jobs and finished %d jobs of %d total jobs in %s" % (current, finished, len(batch.jobs), batch_key))
                    if finished == len(batch.jobs):
                        failures = 0
                        for job_id in batch.jobs:
                            if self.client.exists(job_id):
                                job = pickle.loads(self.client.get(job_id))
                                if job.state == 'failed':
                                    failures += 1
                        logging.info('all batch jobs have been completed, (%d failures)' % failures)
                        batch.state = 'finished'
                        self.client.set(batch_key, pickle.dumps(batch))
                        continue
                    for job_id in batch.jobs:
                        if self.client.exists(job_id):
                            job = pickle.loads(self.client.get(job_id))
                            if job.state == 'spawned' and current < batch.max_nodes:
                                logging.info('detected empty slot (%d/%d) for %s, creating job' % ( batch.max_nodes-current, batch.max_nodes, batch_key))
                                job.state = 'received'
                                self.client.set(job_id, pickle.dumps(job))
                                self.client.publish('jobs', job_id)
                                current += 1
            except Exception, e:
                logging.exception('failure in %s (%s), continuing..' % (batch_key, e))
