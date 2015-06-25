from datetime import datetime
from flask import Flask

api = Flask(__name__)

@api.route('/')
def index():
    return 'Hello from WJC! (%s)' % datetime.now().strftime('%Y-%m-%d %H:%M:%S')