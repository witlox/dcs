# dcs[![Build Status](https://travis-ci.org/witlox/dcs.svg?branch=master)](https://travis-ci.org/witlox/dcs)
Deltares Cloud Scheduler - Simple Job Queue

Want to have an easy and transparant way to run jobs on Amazon? This might suit you.
We use this software to run simulations on Amazon.

This service consist of 2 working parts;
1. a "controller" running multiple web services (which will be provisioned through docker).
1.1 ILM: Instance Level Manager, manages amazon machines
1.2 WJC: Worker Job Controller, manages the workload and the jobs
1.3 Store: Intermediate file storage

2. a "source" which contains the input data for the "work" and transmits and retreives the "work" (via some scripts).

Part 1 is meant to be run on Amazon, part 2 is meant to be run at your local site (where you have the input data for your simulation and where the result ends up).

.more details will follow.
