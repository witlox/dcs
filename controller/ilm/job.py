class Job:

    ami = None
    instance_type = None

    def __init__(self, state, batch_id):
        self.state = state
        self.batch_id = batch_id

