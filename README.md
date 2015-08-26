# dcs[![Build Status](https://travis-ci.org/witlox/dcs.svg?branch=master)](https://travis-ci.org/witlox/dcs)
Deltares Cloud Scheduler - Simple Job Queue

Want to have an easy and transparent way to run jobs on Amazon? This might suit you.
We use this software to run simulations on Amazon.

This service consist of 2 working parts
- I. a "controller" running multiple web services (which can be provisioned through docker).
  - ILM: Instance Level Manager, manages amazon machines
  - WJC: Worker Job Controller, manages the workload and the jobs

- II. a "source" which contains the input data for the "work" and transmits and retreives the "work" (via some scripts).

Part 1 is meant to be run on Amazon, part 2 is meant to be run at your local site (where you have the input data for your simulation and where the result ends up).

To start the system:
- check if your AWS firewall settings allow the forwarded ports (22/80 for external connections, 22/5000/9200/9300 for worker/controller communication)
- Launch an Amazon image (basic Amazon Linux instance is sufficient, scale the type according to concurrent workload and have a sufficiently large disk)
- sudo yum update -y
- sudo yum install -y docker
- sudo yum install -y git
- sudo service docker start
- sudo usermod -a -G docker ec2-user
- LOG OUT AND LOG IN AGAIN
- git clone https://github.com/witlox/dcs
- cd dcs/controller
- edit the ilm.conf, wjc.conf and start.sh to represent your environment
- create the mount point for storage and database
- run update.sh to get the latest images
- and then simply run the start.sh

The internal mechanics are explained in the readme in the controller directory.

The example folder contains a simple example of how to run jobs on Amazon.

As a user, you will need to download the source directory to your local machine. 
The usage of the scripts is explained in the readme in the source directory.

Good luck!
