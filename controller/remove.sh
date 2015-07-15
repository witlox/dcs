#!/usr/bin/env bash
docker pull elasticsearch
docker pull logstash
docker pull kibana
docker rm web
docker rm store
docker rm ilm
docker rm wjc
docker rm db

