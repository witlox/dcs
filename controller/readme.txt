The controller is the intermediate between the source (client) and the workers. Make sure that the disksize of the controller is sufficient, because at the moment finished jobs will transmit their results to the controller. These will stay there until the source retrieves them.
If you want to run the system on your local (development) machine, install the docker client and run the witlox/dcs container.

We've used as much of the default settings as possible for Nginx (/etc/nginx/nginx.conf) and uWSGI (/usr/share/uwsgi/conf/default.ini)