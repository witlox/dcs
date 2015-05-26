FROM phusion/baseimage:0.9.16

MAINTAINER P. Witlox <pim.witlox@deltares.nl>

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]

# First update repositories
RUN apt-get update

# Install and configure our environment
RUN apt-get install -y build-essential python-dev python-pip nginx git
RUN pip install uwsgi

# Stop nginx if it has started, overwrite default config
RUN service nginx stop
RUN rm /etc/nginx/sites-enabled/default
  
# Get the repository and install reqs
RUN git clone https://github.com/witlox/dcs.git && pip install -r dcs/controller/requirements.txt

# Copy config to correct location and restart nginx
COPY dcs/contoller/nginx.conf /etc/nginx/sites-enabled/dcs.conf
RUN service nginx start

# Start uWSGI, need to convert this to service level start if desired
RUN uwsgi --socket 127.0.0.1:8440 --wsgi-file dcs/controller/ilm.py --callable app --processes 1 --threads 2 --stats 127.0.0.1:9440
RUN uwsgi --socket 127.0.0.1:8441 --wsgi-file dcs/controller/wjc.py --callable app --processes 1 --threads 2 --stats 127.0.0.1:9441

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*