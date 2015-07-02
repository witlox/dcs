from ConfigParser import ConfigParser
from logging.config import dictConfig, logging
import os


class Settings:

    __console_level = 'DEBUG'

    __logstash_level = 'INFO'
    __logstash_host = 'elk'
    __logstash_port = 9300

    def __init__(self):
        logging_config = {
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {
                    'standard': {'format': '[ILM]-%(asctime)s[%(levelname)s](%(name)s):%(message)s',
                                 'datefmt': '%Y-%m-%d %H:%M:%S'},
                    'logstash': {'format': '[ILM]-[%(levelname)s] %(message)s'}
                },
                'handlers': {
                    'fh': {'class': 'logging.StreamHandler',
                           'formatter': 'standard',
                           'level': self.__console_level,
                           'stream': 'ext://sys.stdout'},
                    'ls': {'class': 'logstash.TCPLogstashHandler',
                           'formatter': 'logstash',
                           'level': self.__logstash_level,
                           'host': self.__logstash_host,
                           'port': self.__logstash_port,
                           'version': 1}
                },
                'loggers': {
                    '': {'handlers': ['fh', 'ls'],
                         'level': 'DEBUG',
                         'propagate': True}
                }
            }
        dictConfig(logging_config)
        if not os.exists('ilm.conf'):
            logging.error('we need a valid config, none found!')
            raise
        parser = ConfigParser()
        parser.read('ilm.conf')
        self.aws_region = parser.get('aws', 'region')
        self.aws_secret = parser.get('aws', 'secret_key')
        self.aws_access = parser.get('aws', 'access_key')
        self.aws_seqgrp = parser.get('aws', 'security_group')
