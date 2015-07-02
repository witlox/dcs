from datetime import datetime, timedelta
import json
import logging
import pickle
import requests
from threading import Timer
import paramiko
from settings import Settings

class JobMidwife:
    def __init__(self, client):
        self.settings = Settings()
        self.client = client
        logging.info('starting job midwife crisis')
        self.timer = Timer(60, self.check_newborn)
        self.timer.start()

    def check_newborn(self):
        try:
            for key in self.client.keys('job-*'):
                job = pickle.loads(self.client.get(key))
                if job[2] == 'booted' and job[3] == 'uploaded':
                    ramon = open('ramon.py', 'r').readall().\
                        replace('[wjc]', self.settings.wjc).\
                        replace('[elk]', self.settings.elk).\
                        replace('[store]', self.settings.store).\
                        replace('[uuid]', key)
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    # fish ami
                    r = requests.get('http://%s:6000/ami/%s' % (self.settings.ilm, job[0]))
                    rt = json.loads(r.data)
                    rtup = pickle.loads(rt)
                    with open('%s.pem' % key, 'wb') as hairy:
                        hairy.write(rtup[1])
                    ssh.connect(hostname=job[4], username=rtup[0], key_filename='%s.pem' % key)
                    sftp = ssh.open_sftp()
                    with open('%s.sh' % key, 'w') as smooth:
                        smooth.writelines(ramon)
                    sftp.put('%s.sh' % key, '%s.sh' % key)
                    shell = ssh.invoke_shell()
                    shell.send()
                    shell.send("nohup ./%s.sh > /dev/null 2>&1 &\n" % key)
        except Exception:
            logging.exception('not goig to break our midwife')
