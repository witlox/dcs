The controller is the intermediate between the source (client) and the workers (AMI's).
You will need to build your own worker with the desired computational software installed on Amazon EC2.

The controller consist of 2 web services, ILM and WJC.
These 2 components run under nginx reverse proxy and can run on different machines.
The front-end is ELK.

Make sure that the disksize of the controller is sufficient, because at the moment finished jobs will transmit their results to the controller.
These will stay there until the source explicitly deletes them.
If you want to run the system on your local (development) machine, install the docker client and run the start.sh in the controller root.

There are config files for all the different components, please fix the default settings to represent your environment.

The control flow is as follows:
- start a controller, and specify the AMI (ami id, username, private key) for the worker
- start a store to use for file transfers

As a source (client):
- submit a job ((with source/submit)) in which you specify the specific AMI id and an instance type (http://aws.amazon.com/ec2/instance-types/), it will upload a directory with sub dirs with a 'run' script in the root (chmod +x :) ), this will return a job code

- the controller will pick up the job, start a new worker (ami), start the run script on the worker, the controller will overwrite the work when finished. We assume that the results are in the current working directory of the run!

- the status of the job can be checked during execution (with source/status).

- the source can then download the results to your machine (with source/retrieve)

- delete the job when finished (with source/remove), or turn everything off (or whatever, we're not the fuzz)
