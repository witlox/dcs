#!/usr/bin/env bash
# first pull generic containers
docker pull nginx
docker pull redis
docker pull elasticsearch
docker pull logstash
docker pull kibana
# second pull our own containers
docker pull witlox/ilm
docker pull witlox/wjc

