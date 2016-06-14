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
import socket

from settings import Settings


class JobDictator(threading.Thread):
    def __init__(self):
        with open('logging.json') as jl:
            dictConfig(json.load(jl))
        threading.Thread.__init__(self)
        self.daemon = True
        self.headers = {'User-agent': 'dcs_wjc/1.0'}
        self.settings = Settings()
        self.client = redis.Redis('db')
        self.running = True
        logging.info('JobDictator: Starting.')
        with open('ramon.py', 'r') as r:
            self.ramon = r.read()

    def run(self):
        while self.running:
            self.aladeen()
            sleep(60)

    def aladeen(self):
        for job_id in [job_key for job_key in self.client.keys() if job_key.startswith('job-')]:  # Redis keys(pattern='*') does not filter at all.
            pickled_job = self.client.get(job_id)
            if pickled_job is None:
                continue  # self.client.keys('job-*') is stale
            job = pickle.loads(pickled_job)
            if job.state != 'booted' and job.state != 'running' and job.state != 'run_succeeded' and job.state != 'run_failed':
                continue
            #
            worker = None
            for worker_id in [worker_key for worker_key in self.client.keys() if worker_key.startswith('jm-')]:  # Redis keys(pattern='*') does not filter at all.
                pickled_worker = self.client.get(worker_id)
                if pickled_worker is not None:
                    temp_worker = pickle.loads(pickled_worker)
                    if temp_worker.job_id == job_id:
                        worker = temp_worker
                        break
            if worker is None:
                logging.error('Worker of active job %s not found, failing job.' % job_id)
                job.state = 'failed'
                self.client.set(job_id, pickle.dumps(job))
                continue
            #
            if job.state == 'booted':
                # check if state is ok
                ami_status = requests.get('http://%s/ilm/ami/%s/status' % (self.settings.web, worker.instance),
                                          headers=self.headers)
                if 'status:ok' not in ami_status.content.lower():
                    logging.info('AMI (%s) status (%s) NOK, waiting...' % (worker.instance, ami_status.content))
                    continue
                self.push(job.ami, job.batch_id, job_id, worker, job)
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
                    logging.info('JobDictator: Found a new running job %s.' % job_id)
                    job.run_started_on = datetime.now()
                    self.client.set(job_id, pickle.dumps(job))
                elif datetime.now() - job.run_started_on > timedelta(minutes=int(self.settings.job_timeout)):
                    job.state = 'broken'
                    self.client.set(job_id, pickle.dumps(job))
                    self.client.publish('jobs', job_id)

    def push(self, ami, batch_id, job_id, worker, job):
        """Copy a job to a worker and start the job."""

        logging.info('Found job %s to transmit to worker, preparing script.' % job_id)
        ramon = self.ramon
        ramon = ramon.replace('[web]', self.settings.web)
        ramon = ramon.replace('[elk]', self.settings.elk)
        ramon = ramon.replace('[uuid]', job_id)
        ramon_path = '/tmp/store/%s.sh' % job_id
        ramon_file = '%s.sh' % job_id
        with open(ramon_path, 'w') as smooth:
            smooth.writelines(ramon)
        st_fn = os.stat(ramon_path)
        os.chmod(ramon_path, st_fn.st_mode | stat.S_IEXEC)
        logging.debug('script %s prepared in location %s' % (ramon_file, ramon_path))

        # fish ami
        if ami not in self.client.keys():
            logging.error('Error in push: Unknown AMI %s' % ami)
            job.state = 'failed'
            self.client.set(job_id, pickle.dumps(job))
            self.client.publish('jobs', job_id)
            return
        username, key_file = pickle.loads(self.client.get(ami))
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            logging.info('Establishing connection to push to %s using user %s' % (worker.ip_address, username))
            with open('%s.key' % job_id, 'wb') as hairy:
                hairy.write(key_file)
            try:
                ssh.connect(hostname=worker.ip_address, username=username, key_filename='%s.key' % job_id)

                # Create job directory on the worker.
                try:
                    logging.debug('Creating job directory on the worker.')
                    in_out_err = ssh.exec_command('mkdir %s' % job_id)  # Linux only
                except SSHException as e:
                    logging.error('Failed to preform ssh.exec_command:\n   Stdin: %s\n   Stdout: %s\n   Stderr: %s' % in_out_err)
                    raise RuntimeError('***failed to create a job directory on the worker***')

                # Copy job to the worker.
                luke = '/tmp/store/%s/%s' % (batch_id, job_id)
                with scp.SCPClient(ssh.get_transport()) as s_scp:
                    logging.debug('Copying job data to worker through scp.')
                    s_scp.put(luke, job_id, recursive=True)
                with scp.SCPClient(ssh.get_transport()) as s_scp:
                    logging.debug('Copying job runscript to worker through scp.')
                    s_scp.put(ramon_path, ramon_file)
                os.remove(ramon_path)

                # Set execution bit on job runscript on the worker.
                try:
                    logging.debug('Setting execution bits on job runscript.')
                    in_out_err = ssh.exec_command('chmod +x %s' % ramon_file)  # Linux only
                except SSHException as e:
                    logging.error('Failed to preform ssh.exec_command:\n   Stdin: %s\n   Stdout: %s\n   Stderr: %s' % in_out_err)
                    raise RuntimeError('***failed to set execution bit on job runscript on the worker***')

                # Start the job on the worker.
                start = 'virtualenv venv\nsource venv/bin/activate\npip install --upgrade pip\npip install python-logstash requests\nnohup ./%s  > /dev/null 2>&1 &\n' % ramon_file  # Linux only
                logging.debug('calling remote start with %s' % start)
                _, out, err = ssh.exec_command(start)
                output = out.readlines()
                error = err.readlines()
                if output:
                    logging.info('%s output: %s' % (job_id, output))
                if error:
                    logging.error('%s error: %s' % (job_id, error))
                    raise RuntimeError('error while starting remote job run')
                logging.info('started %s on %s' % (job_id, worker.instance))
            except (paramiko.ssh_exception.BadHostKeyException, paramiko.ssh_exception.AuthenticationException,
                    paramiko.ssh_exception.SSHException, socket.error) as e:
                logging.error('Unable to connect to, or lost connection to worker using ssh: %s' % e.message)
            except Exception as e:
                logging.error('Error in push: %s' % e.message)
                job.state = 'failed'
                self.client.set(job_id, pickle.dumps(job))
                self.client.publish('jobs', job_id)
                logging.warning('Fatal error while starting job %s on worker %s, clean up manually.' % (job_id, worker.instance))

    def pull(self, ami, batch_id, job_id, worker, clean=True, failed=False):
        destination = '/tmp/store/%s/%s' % (batch_id, job_id)
        if os.path.exists(destination):
            try:
                shutil.rmtree(destination)
            except:
                logging.error('Failed to remove directory tree %s' % destination)
                return
        if failed:
            destination += '_failed'
        with paramiko.SSHClient() as ssh:
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            username, key_file = pickle.loads(self.client.get(ami))
            logging.info('establishing connection to pull from %s using user %s' % (worker.ip_address, username))
            with open('%s.key' % job_id, 'wb') as hairy:
                hairy.write(key_file)
            try:
                ssh.connect(hostname=worker.ip_address, username=username, key_filename='%s.key' % job_id)
                with scp.SCPClient(ssh.get_transport()) as s_scp:
                    s_scp.get(job_id, destination, recursive=True)
                if clean:
                    ssh.exec_command('rm -rf %s' % job_id)  # Linux only
                    ssh.exec_command('rm -f %s.sh' % job_id)  # Linux only
                logging.info('transferred results for %s, saved to %s' % (job_id, destination))
            except Exception as e:
                logging.error('Error in pull: %s' % e.message)
                logging.warning('Fatal error while retrieving job %s on worker %s, clean up manually.' % (job_id, worker.instance))
