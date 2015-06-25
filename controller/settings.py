from logging.config import dictConfig, logging


class Settings:

    mongo_url = 'db'
    mongo_port = 27017

    __console_level = 'DEBUG'

    __logstash_level = 'INFO'
    __logstash_host = 'elk'
    __logstash_port = 9300

    def __init__(self, module_name):
        logging_config = {
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {
                    'standard': {'format': '['+module_name+']-%(asctime)s[%(levelname)s](%(name)s):%(message)s',
                                 'datefmt': '%Y-%m-%d %H:%M:%S'},
                    'logstash': {'format': '['+module_name+']-[%(levelname)s] %(message)s'}
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
