from ConfigParser import ConfigParser
import json
from logging.config import dictConfig, logging
import os

dictConfig(json.load('logging.json'))

class Settings:

    def __init__(self, module_name):

        if not os.exists('wjc.conf'):
            logging.error('we need a valid config, none found!')
            raise
        parser = ConfigParser()
        parser.read('wjc.conf')
        self.web = parser.get('parameters', 'web')
        self.elk = parser.get('parameters', 'elk')
