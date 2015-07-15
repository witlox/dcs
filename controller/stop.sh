#!/usr/bin/env bash
docker pull elasticsearch
docker pull logstash
docker pull kibana
docker stop web
docker stop store
docker stop ilm
docker stop wjc
docker stop db

