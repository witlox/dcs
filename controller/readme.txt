The controller is the intermediate between the source (client) and the workers (AMI's).

The controller consist of 3 web services, ILM, WJC and store.
These 3 components run under nginx reverse proxy and can run on different machines.
The front-end is ELK.

Make sure that the disksize of the store is sufficient, because at the moment finished jobs will transmit their results to the store.
These will stay there until the source explicitly deletes them.
If you want to run the system on your local (development) machine, install the docker client and run the start.sh in the controller root.

There are config files for all the different components, please fix the default settings to represent your environment.

The control flow is as follows:
- start a controller, and specify the AMI (account details) for the worker
- start a store to use for file transfers

- submit a job in which you specify the specific AMI id and an instance type.
    -- this will return a job code
- upload a zipped directory ('job_code'.zip) with a 'run' script in the root.

- the controller will pick up the job, start a new worker (ami), start the run script on the worker, retreive the work when finished

- the status of the job can be checked during execution

- the source can then download the results to your machine

- delete the job when finished, or turn everything off (or whatever, we're not the fuzz)
