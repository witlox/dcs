In order to run a job on Amazon with this system, you will need to create an AMI that has the correct software on it.
Everything is run from the user home directory, so make sure that the software you want to use is added to the path.

An AMI can be created using this guide: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/creating-an-ami-ebs.html

When following the creation of a new AMI, you should have set a user (default is ec2-user) and selected or created a key file.

1. Launch a controller (let's assume this is running on the external ip 1.1.1.1).
2. Use the add_ami script in the source directory to register the newly created AMI on the controller. (add_ami 1.1.1.1 some_ami_id worker_ec2-user path/to/key)
3. Use the submit script to upload the 2 directories in this folder (submit 1.1.1.1 controller_user path/to/controller/key some_ami_id t1.micro 2 ['this/dir/test*']).
4. You can use the status script to check progress (status 1.1.1.1 batch_code_from_submit), this should give one finished and one failure.
5. When finished, use the retrieve script to get the results back to your machine (retrieve 1.1.1.1 controller_user path/to/controller/key batch_code_from_submit dir/to/store/results).
6. Use remove to cleanup the batch (remove 1.1.1.1 batch_code_from_submit).

That's all folks.