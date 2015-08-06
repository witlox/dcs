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
        modules = {
            'os': self.os_mock,
            'paramiko' : mock.MagicMock(),
            'requests' : mock.MagicMock(),
            'json': mock.MagicMock(),
            'logging.config': mock.MagicMock(),
            'redis': mock.MagicMock()
        }

        self.module_patcher = mock.patch.dict('sys.modules', modules)
        self.module_patcher.start()

    def tearDown(self):
        self.module_patcher.stop()

    @mock.patch('job_midwife.JobMidwife.__init__', mock.Mock(return_value=None))
    def test_normal_machine_state_flow_for_requested(self):
        self.os_mock.listdir.return_value = ['job-a', 'job-b']

        from job_midwife import JobMidwife
        from job import Job
        from batch import Batch

        midwife = JobMidwife()
        midwife.client = mock.MagicMock()
        midwife.client.keys.return_value = ['batch-']
        midwife.client.exists.return_value = True
        batch = Batch('uploaded')
        batch.max_nodes = 1
        job1 = Job('spawned')
        job2 = Job('spawned')
        midwife.client.get.side_effect = [pickle.dumps(batch), pickle.dumps(job1), pickle.dumps(job2), pickle.dumps(job1), pickle.dumps(job2)]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.sense_blubberies()

        assert midwife.client.get.call_count == 5
        assert midwife.client.set.call_count == 4
        assert midwife.client.publish.call_count == 3

        assert len(midwife.client.set.call_args_list) == 4
        assert pickle.loads(midwife.client.set.call_args_list[3][0][1]).state == 'received'
        assert midwife.client.set.call_args_list[3][0][0] == 'job-a'

if __name__ == '__main__':
    unittest.main()
