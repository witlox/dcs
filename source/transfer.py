import argparse
import os
import requests

parser = argparse.ArgumentParser(description='transfer a zipped directory to the store, note that a "run" file should be in the root.')

parser.add_argument('server', help='specifiy the webserver address')
parser.add_argument('action', help='upload, download or delete the zip file')
parser.add_argument('path', help='path for the file')
parser.add_argument('job_code', help='job code from submit')

args = parser.parse_args()

if args.action not in ('upload', 'download', 'delete'):
    raise Exception('Specify "upload", "download" or "delete" as "up_down_delete" command line argument, not: ' + args.action)

args = args.__dict__

directory, file_name = os.path.split(args['path'])

if args['action'] == 'upload':
    if not os.path.exists(args['path']):
        raise Exception('File does not exist ' + args['path'])
    with open(args['path'], 'rb') as data:
        headers = {'Content-Type': 'application/octet-stream'}
        r = requests.post('http://%s/store/%s' % (args['server'], file_name), data=data.read(), headers=headers)
        if r.status_code != 200:
            raise Exception('Status code not 200, %s' % r.content)
        r = requests.post('http://%s/wjc/jobs/%s/status/uploaded' % (args['server'], args['job_code']))
        print 'upload done %s' % r
elif args['action'] == 'download':
    if not os.path.exists(directory):
        raise Exception('Directory does not exist ' + directory)
    r = requests.get('http://%s/store/%s' % (args['server'], file_name))
    if r.status_code != 200:
        raise Exception('Status code not 200, %s' % r.content)
    with open(args['path'], 'wb') as f:
        f.write(r.content)
    print 'download done to %s' % args['path']
elif args['action'] == 'delete':
    r = requests.delete('http://%s/store/%s' % (args['server'], file_name))
    if r.status_code != 200:
        raise Exception('Status code not 200, %s' % r.content)
    print 'deleting done %s' % r
else:
    print 'what the hell is %s' % args['action']
