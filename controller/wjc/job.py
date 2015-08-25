class Job:
    """
    job runs on instance based on AMI
    states:
        - spawned
        - received
        - requested
        - delayed
        - booted
        - running
        - run_succeeded
        - run_failed
        - finished
        - failed
    """
    ami = None
    instance_type = None
    run_started_on = None

    def __init__(self, state, batch_id):
        self.state = state
        self.batch_id = batch_id
