FROM ubuntu

MAINTAINER P. Witlox <pim.witlox@deltares.nl>

# First update repositories
RUN apt-get update

# Install and configure our environment
RUN apt-get install -y nginx
RUN apt-get install -y supervisor
RUN apt-get install -y python-dev python-pip 
RUN apt-get install -y git
RUN pip install uwsgi

# Add the location for the source
WORKDIR /opt
  
# Get the repository, install requirements and set config
RUN git clone https://github.com/witlox/dcs.git
RUN pip install -r dcs/controller/requirements.txt

# Remove the default and set the new Nginx configuration
RUN rm -v /etc/nginx/nginx.conf
RUN cp dcs/controller/nginx.conf /etc/nginx/nginx.conf

# Append "daemon off;" to the beginning of the configuration
RUN echo "daemon off;" >> /etc/nginx/nginx.conf

# Add the new supervisor config
RUN cp dcs/controller/supervisor.conf /etc/supervisor/conf.d/dcs.conf

# Expose ports
EXPOSE 80

# Start services
CMD service nginx start
CMD service supervisord reload

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
