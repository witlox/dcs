# dcs[![Build Status](https://travis-ci.org/witlox/dcs.svg?branch=master)](https://travis-ci.org/witlox/dcs)
Deltares Cloud Scheduler - Simple Job Queue

Want to have an easy and transparant way to run jobs on Amazon? This might suit you.
We use this software to run simulations on Amazon.

This service consist of 3 working parts;
1. a "controller" running a web service (which will be provisioned through docker).
2. a "worker" defined as a Machine Image that has "worker-software" on it, and a "worker" script that pull's the work.
3. a "source" which contains the input data for the "work" and transmits and retreives the "work" (via some scripts).

Part 1 and 2 are meant to be run on Amazon, part 3 is meant to be run at your local site (where you have the input data for your simulation and where the result ends up).

.more details will follow.
