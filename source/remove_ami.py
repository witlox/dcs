#!/usr/bin/env python

import argparse
import json
import os
import requests

parser = argparse.ArgumentParser(description='remove an existing ami to the system.')

parser.add_argument('server', help='public ip of the web server')
parser.add_argument('ami', help='ami id')

args = parser.parse_args()

args = args.__dict__

headers = {'Content-Type': 'application/json', 'User-agent': 'Luke/1.0'}
r = requests.delete('http://%s/ilm/amis/%s' % (args['server'], args['ami']), headers=headers)
if r.status_code != 200:
    raise Exception('Status code not 200, %s' % r.content)
print 'Removed AMI'
