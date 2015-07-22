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


class JobMidwife(threading.Thread):
    def __init__(self, client):
        logging.info('starting job midwife crisis')
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
        logging.info('checking for job updates')
        for batch_key in self.client.keys('batch-*'):
            batch = pickle.loads(self.client.get(batch_key))
            if batch.state == 'uploaded':
                logging.info('detected uploaded batch %s' % batch_key)
                extract_req = 'http://%s/store/extract/%s.zip' % (self.settings.web, batch_key)
                extract_resp = requests.get(extract_req)
                batch.files = json.loads(extract_resp.content)
                batch.state = 'extracted'
                self.client.set(batch_key, pickle.dumps(batch))
            elif batch.state == 'extracted':
                for job_file in batch.files:
                    current = 0
                    if job_file in self.client.keys('job-*'):
                        job = pickle.loads(self.client.get(job_file))
                        if job.state != 'finished' and job.state != 'failed':
                            current += 1
                if current == len(batch.files):
                    logging.info('all batch jobs have been completed, finalizing')
                    batch.state = 'compressing'
                    self.client.set(batch_key, pickle.dumps(batch))
                    continue
                for job_file in batch.files:
                    if job_file not in self.client.keys('job-*') and current < batch.max_nodes:
                        job = Job('received')
                        job.ami = batch.ami
                        job.instance_type = batch.instance_type
                        self.client.set(job_file, pickle.dumps(job))
                        self.client.publish('jobs', job_file)
                        current += 1
            elif batch.state == 'compressing':
                logging.info('detected finalized batch %s, compressing...' % batch_key)
                data = json.dumps(batch.files)
                compress_req = 'http://%s/store/compress/%s.zip' % (self.settings.web, batch_key)
                requests.post(compress_req, data=data)
                batch.state == 'finished'
                self.client.set(batch_key, pickle.dumps(batch))
        for job_key in self.client.keys('job-*'):
            try:
                job = pickle.loads(self.client.get(job_key))
                # check jobs that have been created by batch, get part by extract, not upload
                if job.state == 'booted':
                    for batch_key in self.client.keys('batch-*'):
                        batch = pickle.loads(self.client.get(batch_key))
                        if batch.state == 'extracted' and job_key in batch.files:
                            job.state = 'uploaded'
                            self.client.set(job_key, pickle.dumps(job))
                if job.state == 'uploaded':
                    # fish ip
                    ip = None
                    for worker_key in self.client.keys('jm-*'):
                        worker = pickle.loads(self.client.get(worker_key))
                        if worker.job_id == job_key:
                            ip = worker.ip_address
                    if ip is None:
                        raise Exception('Could not determine IP address for worker/job %s' % job_key)
                    # check if state is ok
                    ami_stat = 'http://%s/ilm/ami/%s/status' % (self.settings.web, worker.instance)
                    r_stat = requests.get(ami_stat)
                    if not 'status:ok' in r_stat.content.lower():
                        logging.info('AMI (%s) status (%s) NOK, waiting...' % (worker.instance, r_stat.content))
                        continue
                    logging.info('found job to transmit to worker %s, preparing script' % job_key)
                    ramon = None
                    with open('ramon.py', 'r') as r:
                        ramon = r.read()
                    ramon = ramon.replace('[web]', self.settings.web)
                    ramon = ramon.replace('[elk]', self.settings.elk)
                    ramon = ramon.replace('[uuid]', job_key)
                    fn = '%s.sh' % job_key
                    with open(fn, 'w') as smooth:
                        smooth.writelines(ramon)
                    st_fn = os.stat(fn)
                    os.chmod(fn, st_fn.st_mode | stat.S_IEXEC)
                    logging.info('script %s prepared' % fn)
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    # fish ami
                    ami_req = 'http://%s/ilm/ami/%s' % (self.settings.web, job.ami)
                    logging.info('retrieving AMI settings from %s' % ami_req)
                    r_ami = requests.get(ami_req)
                    data = pickle.loads(json.loads(r_ami.content))
                    username = data[0]
                    key_file = data[1]
                    with open('%s.key' % job_key, 'wb') as hairy:
                        hairy.write(key_file)
                    logging.info('establishing connection to %s using user %s' % (ip, username))
                    ssh.connect(hostname=ip, username=username, key_filename='%s.key' % job_key)
                    sftp = ssh.open_sftp()
                    sftp.put(fn, fn)
                    ssh.exec_command('chmod +x %s' % fn)
                    start = 'virtualenv venv\nsource venv/bin/activate\npip install python-logstash requests\nnohup ./%s  > /dev/null 2>&1 &\n' % fn
                    logging.info('calling remote start with %s' % start)
                    _, out, err = ssh.exec_command(start)
                    output = out.readlines()
                    error = err.readlines()
                    if output:
                        logging.info('%s output: %s' % (job_key, output))
                    if error:
                        logging.error('%s error: %s' % (job_key, error))
                    ssh.close()
                    os.remove('%s.key' % job_key)
                    os.remove(fn)
                    logging.info('script should be running now, check kibana for messages')
            except Exception:
                logging.exception('but not going to break our job midwife')
