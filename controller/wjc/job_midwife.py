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
        for key in self.client.keys('job-*'):
            try:
                job = pickle.loads(self.client.get(key))
                if job.state == 'uploaded':
                    # fish ip
                    ip = None
                    for worker_key in self.client.keys('jm-*'):
                        worker = pickle.loads(self.client.get(worker_key))
                        if worker.job_id == key:
                            ip = worker.ip_address
                    if ip is None:
                        raise Exception('Could not determine IP address for worker/job %s' % key)
                    # check if state is ok
                    ami_stat = 'http://%s/ilm/ami/%s/status' % (self.settings.web, worker.instance)
                    r_stat = requests.get(ami_stat)
                    if not 'status:ok' in r_stat.content.lower():
                        logging.info('AMI (%s) status (%s) NOK, waiting...' % (worker.instance, r_stat.content))
                        continue
                    logging.info('found job to transmit to worker %s, preparing script' % key)
                    ramon = None
                    with open('ramon.py', 'r') as r:
                        ramon = r.read()
                    ramon = ramon.replace('[web]', self.settings.web)
                    ramon = ramon.replace('[elk]', self.settings.elk)
                    ramon = ramon.replace('[uuid]', key)
                    fn = '%s.sh' % key
                    with open(fn, 'w') as smooth:
                        smooth.writelines(ramon)
                    st_fn = os.stat(fn)
                    os.chmod(fn, st_fn.st_mode | stat.S_IEXEC)
                    logging.info('wrapper script %s prepared' % fn)
                    sn = 'start-%s.sh' % key
                    with open(sn, 'w') as wrinkly:
                        wrinkly.writelines(['virtualenv venv',
                                            'source venv/bin/activate',
                                            'pip install python-logstash requests',
                                            'nohup ./%s &' % fn])
                    st_sn = os.stat(sn)
                    os.chmod(sn, st_sn.st_mode | stat.S_IEXEC)
                    logging.info('start script %s prepared' % sn)
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    # fish ami
                    ami_req = 'http://%s/ilm/ami/%s' % (self.settings.web, job.ami)
                    logging.info('retrieving AMI settings from %s' % ami_req)
                    r_ami = requests.get(ami_req)
                    data = pickle.loads(json.loads(r_ami.content))
                    username = data[0]
                    key_file = data[1]
                    with open('%s.key' % key, 'wb') as hairy:
                        hairy.write(key_file)
                    logging.info('establishing connection to %s using user %s' % (ip, username))
                    ssh.connect(hostname=ip, username=username, key_filename='%s.key' % key)
                    sftp = ssh.open_sftp()
                    sftp.put(sn, sn)
                    sftp.put(fn, fn)
                    logging.info('transferred scripts, setting up env and calling remote start')
                    ssh.exec_command('chmod +x %s' % sn)
                    ssh.exec_command('chmod +x %s' % fn)
                    _, out, err = ssh.exec_command('./%s &' % sn)
                    output = out.readlines()
                    error = err.readlines()
                    if output:
                        logging.info('%s output: %s' % (key, output))
                    if error:
                        logging.error('%s error: %s' % (key, error))
                    ssh.close()
                    os.remove('%s.key' % key)
                    os.remove(sn)
                    os.remove(fn)
                    logging.info('script should be running now, check kibana for messages')
            except Exception:
                logging.exception('but not going to break our job midwife')
