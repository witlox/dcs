class Worker:

    def __init__(self, job_id, batch_id):
        self.job_id = job_id
        self.batch_id = batch_id

    job_id = None
    batch_id = None
    reservation = None
    instance = None
    request_time = None
    ip_address = None
