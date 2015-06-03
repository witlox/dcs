# We use the flask uwsgi base image from Levi Bracken, it fit's perfectly with our needs (thanks Levi!)
FROM lbracken/flask-uwsgi

MAINTAINER Pim Witlox <pim.witlox@deltares.nl>

# use http for testing purpose only, production use should be behind a nginx reverse proxy using wsgi
#CMD ["uwsgi", "--http :7000 --module api --callable app --processes 2 --threads 4"]

CMD ["uwsgi", "--socket :7000 --module api --callable app --processes 2 --threads 4"]

EXPOSE 7000