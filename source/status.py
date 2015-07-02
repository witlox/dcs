import argparse
import json
import requests

parser = argparse.ArgumentParser(description='get job status from wjc')

parser.add_argument('server', help='specifiy the web server address')
parser.add_argument('job_code', help='job code you got from submit')


args = parser.parse_args()

args = args.__dict__

r = requests.post('http://%s/wjc/jobs/%s/state' % (args['server'], args['job_code']))
print 'your job status is: %s' % r.content
