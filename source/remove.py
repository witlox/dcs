import argparse
import json
import requests

parser = argparse.ArgumentParser(description='remove a job from wjc')

parser.add_argument('server', help='specifiy the web server address')
parser.add_argument('job_code', help='job code you got from submit')


args = parser.parse_args()

args = args.__dict__

r = requests.delete('http://%s/wjc/jobs/%s' % (args['server'], args['job_code']))
print 'your job %s has been deleted (%s)' % (args['job_code'], r.content)
