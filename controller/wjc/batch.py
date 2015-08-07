class Batch:

    ami = None
    instance_type = None
    max_nodes = 0
    jobs = []

    def __init__(self, state):
        self.state = state

