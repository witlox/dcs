FROM ubuntu

MAINTAINER P. Witlox <pim.witlox@deltares.nl>

# First update repositories
RUN apt-get update

# Install and configure our environment
RUN apt-get install -y nginx
RUN apt-get install -y python python-dev python-distribute python-pip 
RUN apt-get install -y uwsgi uwsgi-plugin-python
RUN apt-get install -y git
RUN pip install uwsgi

# we need to install and upgrade zope.interface for uwsgi to work
RUN pip install zope.interface
RUN pip install --upgrade zope.interface

# Add the location for the source
WORKDIR /opt
  
# Get the repository, install requirements and set config
RUN git clone https://github.com/witlox/dcs.git
RUN pip install -r dcs/controller/requirements.txt

# Clean up APT and temp.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Remove the default and set the new Nginx configuration
RUN rm -v /etc/nginx/sites-enabled/default
RUN cp dcs/controller/nginx.conf /etc/nginx/sites-available/dcs
RUN ln -s /etc/nginx/sites-available/dcs /etc/nginx/sites-enabled/dcs

# Append "daemon off;" to the beginning of the configuration
RUN echo "daemon off;" >> /etc/nginx/nginx.conf

# Add the new uwsgi configs
RUN cp dcs/controller/ilm.ini /etc/uwsgi/apps-available/ilm.ini
RUN cp dcs/controller/wjc.ini /etc/uwsgi/apps-available/wjc.ini
RUN ln -s /etc/uwsgi/apps-available/ilm.ini /etc/uwsgi/apps-enabled/ilm.ini
RUN ln -s /etc/uwsgi/apps-available/wjc.ini /etc/uwsgi/apps-enabled/wjc.ini

# Expose ports
EXPOSE 80

# Start services
CMD service nginx restart
CMD service uwsgi restart
