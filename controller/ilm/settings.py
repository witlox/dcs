import json
import os
from logging.config import dictConfig, logging
from ConfigParser import ConfigParser

with open('logging.json') as jl:
    dictConfig(json.load(jl))


class Settings:
    def __init__(self):
        if not os.path.exists('ilm.conf'):
            logging.error('we need a valid config, none found!')
            raise
        parser = ConfigParser()
        parser.read('ilm.conf')
        self.aws_region = parser.get('aws', 'region')
        self.aws_secret = parser.get('aws', 'secret_key')
        self.aws_access = parser.get('aws', 'access_key')
        self.aws_seqgrp = parser.get('aws', 'security_group')
        self.aws_req_max_wait = parser.get('aws', 'request_max_wait_time')
        self.auto_remove_failed = parser.getboolean('parameters', 'auto_remove_failed')
        self.recycle_workers = parser.getboolean('parameters', 'recycle_workers')
        self.max_instances = parser.getint('parameters', 'max_instances')
        self.max_storage = parser.getint('parameters', 'max_storage')
