class Batch:
    """
    batch runs set of jobs with limiter on concurrent size for instance of AMI
    states:
        - received
        - running
        - finished
    """
    ami = None
    instance_type = None
    max_nodes = 0
    jobs = None

    def __init__(self, state):
        self.state = state

