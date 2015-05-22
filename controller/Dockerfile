FROM phusion/baseimage:0.9.16

MAINTAINER P. Witlox <pim.witlox@deltares.nl>

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]

# First update repositories
RUN apt-get update && apt-get upgrade

# Install and configure our environment
RUN apt-get install -y build-essential python-dev python-pip nginx git wget
RUN pip install uwsgi

# Stop nginx if it has started, overwrite default config, and restart
RUN service nginx stop
RUN wget -q https://raw.githubusercontent.com/witlox/dcs/master/contoller/nginx.conf -O /etc/nginx.conf
RUN service nginx start
  
# Get the repository and install reqs
RUN git clone https://github.com/witlox/dcs.git && pip install -r dcs/controller/requirements.txt

# start uWSGI, need to convert this to service level start if desired
RUN uwsgi --socket 127.0.0.1:8440 --wsgi-file dcs/controller/ilm.py --callable app --processes 1 --threads 1 --stats 127.0.0.1:9440
RUN uwsgi --socket 127.0.0.1:8441 --wsgi-file dcs/controller/wjc.py --callable app --processes 1 --threads 1 --stats 127.0.0.1:9441
