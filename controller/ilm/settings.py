import json
import os
from logging.config import dictConfig, logging
from ConfigParser import ConfigParser

with open('logging.json') as jl:
    dictConfig(json.load(jl))

class Settings:

    def __init__(self):
        if not os.exists('ilm.conf'):
            logging.error('we need a valid config, none found!')
            raise
        parser = ConfigParser()
        parser.read('ilm.conf')
        self.aws_region = parser.get('aws', 'region')
        self.aws_secret = parser.get('aws', 'secret_key')
        self.aws_access = parser.get('aws', 'access_key')
        self.aws_seqgrp = parser.get('aws', 'security_group')
