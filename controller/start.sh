# first pull the required containers
docker pull nginx
docker pull mongo
# second pull our own containers
docker pull witlox/ilm
docker pull witlox/wjc
# start the database backend (runs on port 27017)
docker run --name dcs-mongo -d mongo
# start nginx with the overwritten default site (port 80)
docker run -p 80:80 --name dcs-nginx -v nginx.conf:/etc/nginx/sites-enabled/default:ro -d nginx
# start uwsgi containers with overwritten config and mounted apps (ports 6000 & 7000)
docker run --name dcs-ilm -d witlox/ilm
docker run --name dcs-wjc -d witlox/wjc
# and now everything should be up and running


