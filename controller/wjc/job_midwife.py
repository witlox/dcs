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
                    ramon = None
                    with open ("data.txt", "r") as r:
                        ramon = r.read()
                    ramon = ramon.replace('[web]', self.settings.web)
                    ramon = ramon.replace('[elk]', self.settings.elk)
                    ramon = ramon.replace('[uuid]', key)
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    # fish ami
                    r = requests.get('http://%s/ilm/ami/%s' % (self.settings.web, job.ami))
                    rt = json.loads(r.data)
                    rtup = pickle.loads(rt)
                    with open('%s.pem' % key, 'wb') as hairy:
                        hairy.write(rtup[1])
                    # fish ip
                    ip = None
                    for worker_key in self.client.keys('jm-*'):
                        worker = pickle.loads(self.client.get(worker_key))
                        if worker.job_id == key:
                            ip = worker.ip_address
                    if ip is None:
                        raise Exception('Could not determine IP address for worker/job %s' % key)
                    ssh.connect(hostname=ip, username=rtup[0], key_filename='%s.pem' % key)
                    sftp = ssh.open_sftp()
                    fn = '%s.sh' % key
                    with open(fn, 'w') as smooth:
                        smooth.writelines(ramon)
                    st = os.stat(fn)
                    os.chmod(fn, st.st_mode | stat.S_IEXEC)
                    sftp.put(fn, fn)
                    shell = ssh.invoke_shell()
                    shell.send()
                    shell.send("nohup ./%s > /dev/null 2>&1 &\n" % fn)
                    ssh.close()
            except Exception:
                logging.exception('but not going to break our job midwife')
