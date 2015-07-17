import json
import logging
import os
import pickle
import requests
import stat
from threading import Timer
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
                    logging.info('getting worker ip')
                    ip = None
                    for worker_key in self.client.keys('jm-*'):
                        worker = pickle.loads(self.client.get(worker_key))
                        if worker.job_id == key:
                            ip = worker.ip_address
                    if ip is None:
                        raise Exception('Could not determine IP address for worker/job %s' % key)
                    # check if state is ok
                    ami_stat = 'http://%s/ilm/ami/%s' % (self.settings.web, worker.instance)
                    logging.info('retrieving AMI (%s) status: %s' % (worker.instance, ami_stat))
                    if ami_stat.lower() != 'status:ok':
                        logging.info('AMI (%s) NOK, waiting...' % ami_stat)
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
                    st = os.stat(fn)
                    os.chmod(fn, st.st_mode | stat.S_IEXEC)
                    logging.info('script %s prepared' % fn)
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    # fish ami
                    ami_req = 'http://%s/ilm/ami/%s' % (self.settings.web, job.ami)
                    logging.info('retrieving AMI settings from %s' % ami_req)
                    r = requests.get(ami_req)
                    data = pickle.loads(json.loads(r.content))
                    username = data[0]
                    key_file = data[1]
                    with open('%s.key' % key, 'wb') as hairy:
                        hairy.write(key_file)
                    logging.info('establishing connection to %s using user %s' % (ip, username))
                    ssh.connect(hostname=ip, username=username, key_filename='%s.key' % key)
                    sftp = ssh.open_sftp()
                    sftp.put(fn, fn)
                    logging.info('transferred script, setting up env and calling remote start')
                    _, out, err = ssh.exec_command('virtualenv venv && '
                                                   'source venv/bin/activate && '
                                                   'pip install python-logstash requests && '
                                                   'chmod +x %s && '
                                                   'nohup ./%s > /dev/null 2>&1' % (fn, fn))
                    output = out.readlines()
                    error = err.readlines()
                    if output:
                        logging.info('%s output: %s' % (key, output))
                    if error:
                        logging.error('%s error: %s' % (key, error))
                    ssh.close()
                    os.remove('%s.key' % key)
                    os.remove(fn)
                    logging.info('script should be running now, check kibana for messages')
            except Exception:
                logging.exception('but not going to break our job midwife')
