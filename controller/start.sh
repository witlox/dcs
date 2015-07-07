#!/usr/bin/env bash
# if containers are running on different machines, use --add-host="name:ip" to redirect (ex: elk:x.x.x.x)
# first pull the required containers
docker pull nginx
docker pull redis
docker pull pblittle/docker-logstash
# second pull our own containers
docker pull witlox/store
docker pull witlox/ilm
docker pull witlox/wjc
# start the database backend (runs on port 27017, mount a local volume that will store database)
docker run --name db -v /tmp/data:/data -d redis
# start the file store (mount a local volume that will store the intermediate files)
docker run --name store -v /tmp/store:/tmp/store -d witlox/store
# start the logstash backend (logstash on port 9200, kibana on port 9292), open 9200 for worker logging
docker run -p 9200:9200 -p 9300:9300 -e LOGSTASH_CONFIG_URL=https://raw.githubusercontent.com/witlox/dcs/master/controller/logstash.conf --name elk -d pblittle/docker-logstash
# start uwsgi containers with overwritten config and mounted apps (ports 6000 & 7000)
docker run --name ilm --link db:db --link elk:elk -v $(pwd)/ilm.conf:/var/www/app/ilm.conf:ro -d witlox/ilm
docker run --name wjc --link db:db --link elk:elk -v $(pwd)/wjc.conf:/var/www/app/wjc.conf:ro -d witlox/wjc
# start nginx with the overwritten default site (port 80)
docker run -p 80:80 --name web --link elk:elk --link ilm:ilm --link wjc:wjc --link store:store -v $(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro -d nginx
# and now everything should be up and running
