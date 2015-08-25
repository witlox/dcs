#!/usr/bin/env python

import io
import os
import stat
import subprocess
from logging.config import dictConfig, logging

import requests

dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': '%(asctime)s[%(levelname)s]%(funcName)s:%(message)s',
                     'datefmt': '%Y-%m-%d %H:%M:%S'},
        'logstash': {'format': '[%(levelname)s][uuid]:%(message)s'}
    },
    'handlers': {
        'fh': {'class': 'logging.StreamHandler',
               'formatter': 'standard',
               'level': 'DEBUG',
               'stream': 'ext://sys.stdout'},
        'ls': {'class': 'logstash.TCPLogstashHandler',
               'formatter': 'logstash',
               'level': 'INFO',
               'host': '[elk]',
               'port': 5000,
               'version': 1}
    },
    'loggers': {
        '': {'handlers': ['fh', 'ls'],
             'level': 'DEBUG',
             'propagate': True}
    }
})

try:
    headers = {'User-agent': 'Ramon/1.0'}
    # go to our work dir
    os.chdir('[uuid]')
    # run chmod +x on run script
    st = os.stat('run')
    os.chmod('run', st.st_mode | stat.S_IEXEC)
    # start the 'run' script
    r = requests.post('http://[web]/wjc/jobs/[uuid]/state/running', headers=headers)
    output_filename = 'output.log'
    error_filename = 'error.log'
    # mwahahaha, buffer outputs and write them to loggers during execution (non blocking)
    with io.open(output_filename, 'wb') as output_writer, io.open(output_filename, 'rb', 1) as output_reader, \
            io.open(error_filename, 'wb') as error_writer, io.open(error_filename, 'rb', 1) as error_reader:
        process = subprocess.Popen('./run', shell=True, stdout=output_writer, stderr=error_writer)
        while process.poll() is None:
            output_line = output_reader.read()
            error_line = error_reader.read()
            if output_line is not None and len(output_line) > 0:
                logging.info(output_line)
            if error_line is not None and len(error_line) > 0:
                logging.error(error_line)
        process.wait()
        output_line = output_reader.read()
        if output_line is not None and len(output_line) > 0:
            logging.info(output_line)
        error_line = error_reader.read()
        if error_line is not None and len(error_line) > 0:
            logging.error(error_line)
    # finished
    if process.returncode != 0:
        r = requests.post('http://[web]/wjc/jobs/[uuid]/state/run_failed', headers=headers)
        logging.error('Job returned error code %s' % str(process.returncode))
    else:
        r = requests.post('http://[web]/wjc/jobs/[uuid]/state/run_succeeded', headers=headers)
        logging.info('job [uuid] done')
except Exception, e:
    logging.exception('Failed to complete work %s' % e)
    r = requests.post('http://[web]/wjc/jobs/[uuid]/state/run_failed', headers=headers)
