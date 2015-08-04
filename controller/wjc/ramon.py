#!/usr/bin/env python

import io
import os
import requests
import stat
import subprocess
import zipfile
import shutil
from logging.config import dictConfig, logging

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
    # go get our stuff
    r = requests.post('http://[web]/wjc/jobs/[uuid]/state/downloading')
    logging.info('downloading')
    r = requests.get('http://[web]/store/[uuid].zip', stream=True)
    if r.status_code != 200:
        raise Exception('could not download [uuid].zip')
    with open('[uuid].zip', 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                f.flush()
    # extract to work dir
    os.mkdir('[uuid]')
    os.chdir('[uuid]')
    # unzip the file
    r = requests.post('http://[web]/wjc/jobs/[uuid]/state/extracting')
    with zipfile.ZipFile('../[uuid].zip', allowZip64=True) as zf:
        zf.extractall()
    # reset permissions
    for root, dirs, files in os.walk('.'):
        for momo in dirs:
            os.chown(os.path.join(root, momo), os.getuid(), os.getgid())
        for momo in files:
            os.chown(os.path.join(root, momo), os.getuid(), os.getgid())
    # run chmod +x
    st = os.stat('run')
    os.chmod('run', st.st_mode | stat.S_IEXEC)
    # start the 'run' script
    r = requests.post('http://[web]/wjc/jobs/[uuid]/state/running')
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
    failure = process.returncode != 0
    # zip the results
    r = requests.post('http://[web]/wjc/jobs/[uuid]/state/compressing')
    os.remove('../[uuid].zip')
    with zipfile.ZipFile('../[uuid].zip', 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as ozf:
        for dir_path, dir_names, file_names in os.walk('.'):
            for fname in file_names:
                path = os.path.normpath(os.path.join(dir_path, fname))
                if os.path.isfile(path):
                    ozf.write(path, path)
    # upload the results
    r = requests.post('http://[web]/wjc/jobs/[uuid]/state/uploading')
    # remove old file on store
    r = requests.delete('http://[web]/store/[uuid].zip')
    with open('../[uuid].zip', 'rb') as f:
        r = requests.post('http://[web]/store/[uuid].zip', data=f)
        if r.status_code != 200:
            raise Exception('could not upload results')
    # finished
    if failure:
        r = requests.post('http://[web]/wjc/jobs/[uuid]/state/failed')
        logging.error('Job returned error code %s' % str(process.returncode))
    else:
        r = requests.post('http://[web]/wjc/jobs/[uuid]/state/finished')
        logging.info('job [uuid] done')
except Exception:
    logging.exception('Failed to complete work')
    r = requests.post('http://[web]/wjc/jobs/[uuid]/state/failed')
