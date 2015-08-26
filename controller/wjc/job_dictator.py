from datetime import datetime, timedelta
import json
import logging
from logging.config import dictConfig
import os
import pickle
import shutil
import stat
import threading
from time import sleep
import redis
import requests
import paramiko
import scp

from settings import Settings


class JobDictator(threading.Thread):
    def __init__(self):
        with open('logging.json') as jl:
            dictConfig(json.load(jl))
        logging.info('starting job midwife crisis')
        threading.Thread.__init__(self)
        self.daemon = True
        self.headers = {'User-agent': 'dcs_wjc/1.0'}
        self.settings = Settings()
        self.client = redis.Redis('db')

    def run(self):
        for job_id in self.client.keys('job-*'):
            job = pickle.loads(self.client.get(job_id))
            if job.state != 'booted' and job.state != 'running' and job.state != 'run_succeeded' and job.state != 'run_failed':
                continue
            try:
                worker = None
                for worker_key in self.client.keys('jm-*'):
                    temp_worker = pickle.loads(self.client.get(worker_key))
                    if temp_worker.job_id == job_id:
                        worker = temp_worker
                if job.state == 'booted':
                    # check if state is ok
                    ami_status = requests.get('http://%s/ilm/ami/%s/status' % (self.settings.web, worker.instance), headers=self.headers)
                    if 'status:ok' not in ami_status.content.lower():
                        logging.info('AMI (%s) status (%s) NOK, waiting...' % (worker.instance, ami_status.content))
                        continue
                    self.push(job.ami, job.batch_id, job_id, worker)
                elif job.state == 'run_succeeded' or job.state == 'run_failed':
                    self.pull(job.ami, job.batch_id, job_id, worker)
                    if job.state == 'run_succeeded':
                        job.state = 'finished'
                    elif job.state == 'run_failed':
                        job.state = 'failed'
                    self.client.set(job_id, pickle.dumps(job))
                    self.client.publish('jobs', job_id)
                elif job.state == 'running':
                    if job.run_started_on is None:
                        job.run_started_on = datetime.now()
                        self.client.set(job_id, pickle.dumps(job))
                    elif datetime.now() - job.run_started_on > timedelta(minutes=int(self.settings.job_timeout)):
                        self.pull(job.ami, job.batch_id, job_id, worker)
                        raise RuntimeError('job timed out')
            except Exception, e:
                job.state = 'failed'
                self.client.set(job_id, pickle.dumps(job))
                self.client.publish('jobs', job_id)
                logging.exception('failure in %s, failing job (%s)' % (job_id, e))
        sleep(60)

    def push(self, ami, batch_id, job_id, worker):
        logging.info('found job to transmit to worker %s, preparing script' % job_id)
        ramon = None
        with open('ramon.py', 'r') as r:
            ramon = r.read()
        ramon = ramon.replace('[web]', self.settings.web)
        ramon = ramon.replace('[elk]', self.settings.elk)
        ramon = ramon.replace('[uuid]', job_id)
        ramon_file = '%s.sh' % job_id
        with open(ramon_file, 'w') as smooth:
            smooth.writelines(ramon)
        st_fn = os.stat(ramon_file)
        os.chmod(ramon_file, st_fn.st_mode | stat.S_IEXEC)
        logging.debug('script %s prepared' % ramon_file)
        # fish ami
        username, key_file = pickle.loads(self.client.get(ami))
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            logging.info('establishing connection to push to %s using user %s' % (worker.ip_address, username))
            with open('%s.key' % job_id, 'wb') as hairy:
                hairy.write(key_file)
            ssh.connect(hostname=worker.ip_address, username=username, key_filename='%s.key' % job_id)
            with scp.SCPClient(ssh.get_transport()) as s_scp:
                luke = '/tmp/store/%s/%s' % (batch_id, job_id)
                ssh.exec_command('mkdir %s' % job_id)
                s_scp.put(luke, job_id, recursive=True)
                s_scp.put(ramon_file, ramon_file)
            ssh.exec_command('chmod +x %s' % ramon_file)
            start = 'virtualenv venv\nsource venv/bin/activate\npip install python-logstash requests\nnohup ./%s  > /dev/null 2>&1 &\n' % ramon_file
            logging.debug('calling remote start with %s' % start)
            _, out, err = ssh.exec_command(start)
            output = out.readlines()
            error = err.readlines()
            if output:
                logging.info('%s output: %s' % (job_id, output))
            if error:
                logging.error('%s error: %s' % (job_id, error))
                raise RuntimeError('error while executing remote run')
        os.remove(ramon_file)
        logging.info('started %s on %s' % (job_id, worker.instance))

    def pull(self, ami, batch_id, job_id, worker, clean=True, failed=False):
        destination = '/tmp/store/%s/%s' % (batch_id, job_id)
        if os.path.exists(destination):
            shutil.rmtree(destination)
        if failed:
            destination += '_failed'
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            username, key_file = pickle.loads(self.client.get(ami))
            logging.info('establishing connection to pull from %s using user %s' % (worker.ip_address, username))
            with open('%s.key' % job_id, 'wb') as hairy:
                hairy.write(key_file)
            ssh.connect(hostname=worker.ip_address, username=username, key_filename='%s.key' % job_id)
            with scp.SCPClient(ssh.get_transport()) as s_scp:
                s_scp.get(job_id, destination, recursive=True)
            if clean:
                ssh.exec_command('rm -rf %s' % job_id)
                ssh.exec_command('rm -f %s.sh' % job_id)
        logging.info('transferred results for %s, saved to %s' % (job_id, destination))
