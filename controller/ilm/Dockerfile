# We use the flask uwsgi base image from Levi Bracken, it fit's perfectly with our needs (thanks Levi!)
FROM lbracken/flask-uwsgi

MAINTAINER Pim Witlox <pim.witlox@deltares.nl>

CMD ["uwsgi", "--socket", ":6000", "--module", "api", "--callable", "app", "--processes", "2", "--threads", "6"]

EXPOSE 6000