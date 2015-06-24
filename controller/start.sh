# first pull the required containers
docker pull nginx
docker pull mongo
# second pull our own containers
docker pull witlox/ilm
docker pull witlox/wjc
# start the database backend (runs on port 27017)
docker run --name db -d mongo
# start uwsgi containers with overwritten config and mounted apps (ports 6000 & 7000)
docker run --name ilm --link db:db -d witlox/ilm
docker run --name wjc --link db:db -d witlox/wjc
# start nginx with the overwritten default site (port 80)
docker run -p 80:80 --name web --link ilm:ilm --link wjc:wjc -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro -d nginx
# and now everything should be up and running
