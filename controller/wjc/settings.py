from ConfigParser import ConfigParser
import json
from logging.config import dictConfig, logging
import os

with open('logging.json') as jl:
    dictConfig(json.load(jl))

class Settings:

    def __init__(self):
        if not os.path.exists('wjc.conf'):
            logging.error('we need a valid config, none found!')
            raise
        parser = ConfigParser()
        parser.read('wjc.conf')
        self.web = parser.get('parameters', 'web')
        self.elk = parser.get('parameters', 'elk')
