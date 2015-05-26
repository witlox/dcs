FROM phusion/baseimage:0.9.16

MAINTAINER P. Witlox <pim.witlox@deltares.nl>

# First update repositories
RUN apt-get update

# Install and configure our environment
RUN apt-get install -y build-essential python-dev python-pip nginx supervisor git
RUN pip install uwsgi

# Stop nginx if it has started, remove default config
RUN service nginx stop
RUN rm /etc/nginx/sites-enabled/default
  
# Get the repository, install requirements and set config
RUN git clone https://github.com/witlox/dcs.git && pip install -r dcs/controller/requirements.txt
RUN ln -s ./dcs/controller/nginx.conf /etc/nginx/sites-enabled
RUN ln -s ./dcs/controller/supervisor.conf /etc/supervisor/conf.d/

# Start services
expose 80
cmd ["supervisord", "-n"]

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
