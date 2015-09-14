from datetime import datetime, timedelta
import os
import pickle
import shutil
import unittest
import mock


# don't want to create packages
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.split(__file__)[0] , '../controller/wjc')))


class TestWjc(unittest.TestCase):
    def setUp(self):
        if os.getcwd() != os.path.split(os.path.abspath(__file__))[0]:
            shutil.copy(os.path.join(os.path.split(os.path.abspath(__file__))[0], 'logging.json'), 'logging.json')
        self.os_mock = mock.MagicMock()
        self.request_mock = mock.MagicMock()
        modules = {
            'os': self.os_mock,
            'paramiko' : mock.MagicMock(),
            'requests' : self.request_mock,
            'json': mock.MagicMock(),
            'logging.config': mock.MagicMock(),
            'redis': mock.MagicMock(),
            'time': mock.MagicMock()
        }

        self.module_patcher = mock.patch.dict('sys.modules', modules)
        self.module_patcher.start()

    def tearDown(self):
        self.module_patcher.stop()

    @mock.patch('job_dictator.JobDictator.__init__', mock.Mock(return_value=None))
    def test_booted(self):

        from job_dictator import JobDictator
        from job import Job
        from worker import Worker

        dictator = JobDictator()
        dictator.client = mock.MagicMock()
        dictator.client.keys.return_value = ['job-']
        job = Job('booted', 'something')
        worker = Worker('job-', None)
        dictator.client.get.side_effect = [pickle.dumps(job), pickle.dumps(worker)]
        self.request_mock.get = mock.MagicMock()
        dictator.settings = mock.MagicMock()
        dictator.headers = mock.MagicMock()
        returner = mock.MagicMock()
        returner.content = 'status:ok'
        self.request_mock.get.return_value = returner
        dictator.push = mock.MagicMock()

        dictator.aladeen()

        assert dictator.client.keys.call_count == 2
        assert dictator.client.get.call_count == 2
        assert dictator.push.call_count == 1

    @mock.patch('job_dictator.JobDictator.__init__', mock.Mock(return_value=None))
    def test_run_result(self):

        from job_dictator import JobDictator
        from job import Job
        from worker import Worker

        dictator = JobDictator()
        dictator.client = mock.MagicMock()
        dictator.client.keys.return_value = ['job-']
        job = Job('run_succeeded', 'something')
        worker = Worker('job-', None)
        dictator.client.get.side_effect = [pickle.dumps(job), pickle.dumps(worker)]
        self.request_mock.get = mock.MagicMock()
        dictator.settings = mock.MagicMock()
        dictator.headers = mock.MagicMock()
        returner = mock.MagicMock()
        returner.content = 'status:ok'
        self.request_mock.get.return_value = returner
        dictator.pull = mock.MagicMock()

        dictator.aladeen()

        assert dictator.client.keys.call_count == 2
        assert dictator.client.get.call_count == 2
        assert dictator.client.set.call_count == 1
        assert dictator.client.publish.call_count == 1
        assert dictator.pull.call_count == 1

    @mock.patch('job_dictator.JobDictator.__init__', mock.Mock(return_value=None))
    def test_run_timeout(self):

        from job_dictator import JobDictator
        from job import Job
        from worker import Worker

        dictator = JobDictator()
        dictator.client = mock.MagicMock()
        dictator.client.keys.return_value = ['job-']
        job = Job('running', 'something')
        job.run_started_on = datetime.now() - timedelta(minutes=10)
        worker = Worker('job-', None)
        dictator.client.get.side_effect = [pickle.dumps(job), pickle.dumps(worker)]
        self.request_mock.get = mock.MagicMock()
        dictator.settings = mock.MagicMock()
        dictator.settings.job_timeout = 1
        dictator.headers = mock.MagicMock()
        returner = mock.MagicMock()
        returner.content = 'status:ok'
        self.request_mock.get.return_value = returner
        dictator.pull = mock.MagicMock()

        dictator.aladeen()

        assert dictator.client.keys.call_count == 2
        assert dictator.client.get.call_count == 2
        assert dictator.client.set.call_count == 1
        assert dictator.client.publish.call_count == 1
        assert dictator.pull.call_count == 1
        assert pickle.loads(dictator.client.set.call_args_list[0][0][1]).state == 'failed'

    @mock.patch('batch_midwife.BatchMidwife.__init__', mock.Mock(return_value=None))
    def test_batch_job_spawn(self):
        self.os_mock.listdir = mock.MagicMock()
        self.os_mock.listdir.return_value = ['job-dir1', 'job-dir2']

        from batch_midwife import BatchMidwife
        from batch import Batch

        midwife = BatchMidwife()
        midwife.apprentice = mock.MagicMock()
        midwife.client = mock.MagicMock()
        midwife.job_pub_sub = mock.MagicMock()
        midwife.job_pub_sub.listen.return_value = [{'data': 'batch-lovelyhashcode'}]
        midwife.client.exists.return_value = True
        batch = Batch('uploaded')
        midwife.client.get.return_value = pickle.dumps(batch)
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.run()

        assert midwife.client.exists.call_count == 1
        assert midwife.client.get.call_count == 1
        assert midwife.client.set.call_count == 4
        assert midwife.client.publish.call_count == 2
        assert midwife.client.set.call_args_list[1][0][0] == 'job-dir1batch-lovelyhashcode'
        assert midwife.client.set.call_args_list[2][0][0] == 'job-dir2batch-lovelyhashcode'
        assert pickle.loads(midwife.client.set.call_args_list[3][0][1]).state == 'running'
        assert self.os_mock.listdir.call_count == 1


if __name__ == '__main__':
    unittest.main()
