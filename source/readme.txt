This is the source (Luke).

The scripts require requests module:
pip install -r requirements.txt

These scripts facilitate the communication and data transfer to and from the controller.
"add_ami" is needed to register new AMI's on the controller.
"remove" cleans up after a batch is finished.
"status" retrieves the current state of the batch.
"submit" creates a new batch.
"retrieve" is needed to download files from the controller.
"signal" kill a job.
