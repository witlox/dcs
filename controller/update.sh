#!/usr/bin/env bash
# if containers are running on different machines, use --add-host="name:ip" to redirect (ex: elk:x.x.x.x)
docker pull nginx
docker pull redis
docker pull pblittle/docker-logstash
# second pull our own containers
docker pull witlox/store
docker pull witlox/ilm
docker pull witlox/wjc

