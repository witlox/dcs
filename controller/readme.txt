The controller is the intermediate between the source (client) and the workers.
Make sure that the disksize of the controller is sufficient, because at the moment finished jobs will transmit their results to the controller.
These will stay there until the source retrieves them.
If you want to run the system on your local (development) machine, install the docker client and run the start.sh in the controller root.

The control flow is as follows:
- start a controller, and specify the account details for the worker
- start a store to use for file transfers
- start a source, in which you specify the job (currently a 'run' script in the root)
- the controller will pick up the job, start a new worker (ami), start the run script on the worker, retreive the work when finished
- the source will then download the results to your machine

The source can be run as a continuous script, or as a single step in the process.