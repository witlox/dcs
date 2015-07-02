# We use the flask uwsgi base image from Levi Bracken, it fit's perfectly with our needs (thanks Levi!)
FROM lbracken/flask-uwsgi

MAINTAINER Pim Witlox <pim.witlox@deltares.nl>

# the files are stored in /tmp/store by default, this value can be overwritten with the environment variable "store"
CMD ["uwsgi", "--socket", ":7999", "--module", "api", "--callable", "app", "--processes", "2", "--threads", "4"]

EXPOSE 7999