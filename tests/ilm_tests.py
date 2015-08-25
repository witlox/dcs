from datetime import datetime, timedelta
import os
import pickle
import shutil
import unittest
import mock


# don't want to create packages
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.split(__file__)[0] , '../controller/ilm')))


class TestIlm(unittest.TestCase):
    def setUp(self):
        if os.getcwd() != os.path.split(os.path.abspath(__file__))[0]:
            shutil.copy(os.path.join(os.path.split(os.path.abspath(__file__))[0], 'logging.json'), 'logging.json')
        self.aws_mock = mock.MagicMock()
        modules = {
            'aws': self.aws_mock,
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

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.choke_full', mock.Mock(return_value=False))
    def test_normal_machine_state_flow_for_received(self):
        self.aws_mock.start_machine = mock.MagicMock()
        self.aws_mock.start_machine.return_value = 'jm-', 'res0'

        from machine_midwife import MachineMidwife
        from job import Job

        midwife = MachineMidwife()
        midwife.apprentice = mock.MagicMock()
        midwife.settings = mock.MagicMock()
        midwife.client = mock.MagicMock()
        midwife.job_pub_sub = mock.MagicMock()
        midwife.job_pub_sub.listen.return_value = [{'data': 'test'}]
        midwife.client.exists.return_value = True
        job = Job('received', 'something')
        midwife.client.get.side_effect = [pickle.dumps(job), pickle.dumps(job)]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.run()

        assert midwife.client.exists.call_count == 2
        assert len(midwife.client.set.call_args_list) == 2
        assert midwife.client.set.call_args_list[0][0][0] == 'jm-'
        assert midwife.client.set.call_args_list[1][0][0] == 'test'
        assert self.aws_mock.start_machine.call_count == 1
        assert pickle.loads(midwife.client.set.call_args_list[1][0][1]).state == 'requested'

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.choke_full', mock.Mock(return_value=True))
    def test_delay_machine_state_flow_for_requested(self):
        from machine_midwife import MachineMidwife
        from job import Job

        midwife = MachineMidwife()
        midwife.apprentice = mock.MagicMock()
        midwife.settings = mock.MagicMock()
        midwife.client = mock.MagicMock()
        midwife.job_pub_sub = mock.MagicMock()
        midwife.job_pub_sub.listen.return_value = [{'data': 'test'}]
        midwife.client.exists.return_value = True
        job = Job('received', 'something')
        midwife.client.get.side_effect = [pickle.dumps(job), pickle.dumps(job)]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.run()

        assert midwife.client.exists.call_count == 2
        assert len(midwife.client.set.call_args_list) == 1
        assert midwife.client.set.call_args_list[0][0][0] == 'test'
        assert pickle.loads(midwife.client.set.call_args_list[0][0][1]).state == 'delayed'

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.choke_full', mock.Mock(return_value=False))
    def test_requestfailed_machine_state_flow_for_requested(self):
        self.aws_mock.start_machine = mock.MagicMock()
        self.aws_mock.start_machine.return_value = None, None

        from machine_midwife import MachineMidwife
        from job import Job

        midwife = MachineMidwife()
        midwife.apprentice = mock.MagicMock()
        midwife.settings = mock.MagicMock()
        midwife.client = mock.MagicMock()
        midwife.job_pub_sub = mock.MagicMock()
        midwife.job_pub_sub.listen.return_value = [{'data': 'test'}]
        midwife.client.exists.return_value = True
        job = Job('received', 'something')
        midwife.client.get.side_effect = [pickle.dumps(job), pickle.dumps(job)]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.run()

        assert midwife.client.exists.call_count == 2
        assert len(midwife.client.set.call_args_list) == 1
        assert pickle.loads(midwife.client.set.call_args_list[0][0][1]).state == 'failed'

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.choke_full', mock.Mock(return_value=False))
    def test_normal_machine_state_flow_for_requested_with_recycle(self):
        from machine_midwife import MachineMidwife
        from job import Job
        from worker import Worker

        midwife = MachineMidwife()
        midwife.apprentice = mock.MagicMock()
        midwife.settings = mock.MagicMock()
        midwife.client = mock.MagicMock()
        midwife.job_pub_sub = mock.MagicMock()
        midwife.job_pub_sub.listen.return_value = [{'data': 'test'}]
        midwife.client.exists.return_value = True
        job = Job('received', 'batch-')
        worker = Worker(None, 'batch-')
        worker.reservation = 'reservation'
        worker.request_time = datetime.now()
        midwife.client.keys.return_value = ['jm-']
        midwife.client.get.side_effect = [pickle.dumps(job), pickle.dumps(job), pickle.dumps(worker)]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.run()

        assert midwife.client.exists.call_count == 2
        assert len(midwife.client.set.call_args_list) == 2
        assert pickle.loads(midwife.client.set.call_args_list[0][0][1]).job_id == 'test'
        assert pickle.loads(midwife.client.set.call_args_list[1][0][1]).state == 'booted'

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.choke_full', mock.Mock(return_value=False))
    def test_delayed_machine_state_flow_for_requested_with_recycle(self):
        from machine_midwife import MachineMidwife
        from job import Job
        from worker import Worker

        midwife = MachineMidwife()
        midwife.apprentice = mock.MagicMock()
        midwife.settings = mock.MagicMock()
        midwife.client = mock.MagicMock()
        midwife.job_pub_sub = mock.MagicMock()
        midwife.job_pub_sub.listen.return_value = [{'data': 'test'}]
        midwife.client.exists.return_value = True
        job = Job('delayed', 'batch-')
        worker = Worker(None, 'batch-')
        worker.reservation = 'reservation'
        worker.request_time = datetime.now()
        midwife.client.keys.return_value = ['jm-']
        midwife.client.get.side_effect = [pickle.dumps(job), pickle.dumps(job), pickle.dumps(worker)]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.run()

        assert midwife.client.exists.call_count == 2
        assert len(midwife.client.set.call_args_list) == 2
        assert pickle.loads(midwife.client.set.call_args_list[0][0][1]).job_id == 'test'
        assert pickle.loads(midwife.client.set.call_args_list[1][0][1]).state == 'booted'

    @mock.patch('machine_midwife.MachineMidwife.Apprentice.__init__', mock.Mock(return_value=None))
    def test_wake_up_call_for_delayed(self):
        from machine_midwife import MachineMidwife
        Apprentice = MachineMidwife.Apprentice
        from job import Job

        apprentice = Apprentice()
        apprentice.settings = mock.MagicMock()
        apprentice.settings.max_instances = 1
        apprentice.client = mock.MagicMock()
        apprentice.client.exists.return_value = True
        job = Job('delayed', 'batch-')
        apprentice.client.keys.side_effect = [[], ['job-']]
        apprentice.client.get.side_effect = [pickle.dumps(job)]
        apprentice.client.publish = mock.MagicMock()

        apprentice.rise_and_shine()

        assert apprentice.client.keys.call_count == 2
        assert apprentice.client.get.call_count == 1
        assert apprentice.client.publish.call_count == 1

    @mock.patch('machine_midwife.MachineMidwife.Apprentice.__init__', mock.Mock(return_value=None))
    def test_no_wake_up_call_for_delayed(self):
        from machine_midwife import MachineMidwife
        Apprentice = MachineMidwife.Apprentice
        from job import Job
        from worker import Worker

        apprentice = Apprentice()
        apprentice.settings = mock.MagicMock()
        apprentice.settings.max_instances = 1
        apprentice.client = mock.MagicMock()
        apprentice.client.exists.return_value = True
        job = Job('delayed', 'batch-')
        apprentice.client.keys.side_effect = [['jm-1', 'jm-2'], ['job-']]
        w1 = Worker(None, None)
        w1.instance = 'a'
        w2 = Worker(None, None)
        w2.instance = 'b'
        apprentice.client.get.side_effect = [pickle.dumps(w1), pickle.dumps(w2), pickle.dumps(job)]
        apprentice.client.publish = mock.MagicMock()

        apprentice.rise_and_shine()

        assert apprentice.client.keys.call_count == 2
        assert apprentice.client.get.call_count == 3
        assert apprentice.client.publish.call_count == 0

    @mock.patch('machine_midwife.MachineMidwife.Apprentice.__init__', mock.Mock(return_value=None))
    def test_stale_request(self):
        from machine_midwife import MachineMidwife
        Apprentice = MachineMidwife.Apprentice
        from job import Job
        from worker import Worker

        apprentice = Apprentice()
        apprentice.settings = mock.MagicMock()
        apprentice.settings.aws_req_max_wait = 1
        apprentice.client = mock.MagicMock()
        apprentice.client.exists.return_value = True
        job = Job('requested', 'batch-')
        worker = Worker(None, None)
        worker.reservation = 'some'
        worker.request_time = datetime.now() - timedelta(minutes=5)

        apprentice.client.keys.return_value = ['jm-']
        apprentice.client.get.side_effect = [pickle.dumps(worker), pickle.dumps(job)]
        apprentice.client.set = mock.MagicMock()
        apprentice.client.publish = mock.MagicMock()
        apprentice.client.delete = mock.MagicMock()

        apprentice.check_newborn()

        assert apprentice.client.keys.call_count == 1
        assert apprentice.client.get.call_count == 2
        assert apprentice.client.set.call_count == 1
        assert apprentice.client.publish.call_count == 1
        assert apprentice.client.delete.call_count == 1
        assert pickle.loads(apprentice.client.set.call_args_list[0][0][1]).state == 'received'
        assert apprentice.client.delete.call_args_list[0][0][0] == 'jm-'

    @mock.patch('machine_midwife.MachineMidwife.Apprentice.__init__', mock.Mock(return_value=None))
    def test_request_to_booted(self):
        self.aws_mock.my_booted_machine = mock.MagicMock()
        self.aws_mock.my_booted_machine.return_value = 'instance', 'ip'

        from machine_midwife import MachineMidwife
        Apprentice = MachineMidwife.Apprentice
        from job import Job
        from worker import Worker

        apprentice = Apprentice()
        apprentice.settings = mock.MagicMock()
        apprentice.settings.aws_req_max_wait = 10
        apprentice.client = mock.MagicMock()
        apprentice.client.exists.return_value = True
        job = Job('requested', 'batch-')
        worker = Worker(None, None)
        worker.reservation = 'some'
        worker.request_time = datetime.now() - timedelta(minutes=5)

        apprentice.client.keys.return_value = ['jm-']
        apprentice.client.get.side_effect = [pickle.dumps(worker), pickle.dumps(job)]
        apprentice.client.set = mock.MagicMock()
        apprentice.client.publish = mock.MagicMock()

        apprentice.check_newborn()

        assert apprentice.client.keys.call_count == 1
        assert apprentice.client.get.call_count == 2
        assert apprentice.client.set.call_count == 2
        assert apprentice.client.publish.call_count == 1
        assert pickle.loads(apprentice.client.set.call_args_list[0][0][1]).instance == 'instance'
        assert pickle.loads(apprentice.client.set.call_args_list[1][0][1]).state == 'booted'

    @mock.patch('consuela.Consuela.__init__', mock.Mock(return_value=None))
    def test_normal_machine_removal(self):
        from consuela import Consuela
        from job import Job
        from worker import Worker

        with mock.patch('consuela.terminate_worker') as worker_mock:

            cleaner = Consuela()
            cleaner.job_pub_sub = mock.MagicMock()
            cleaner.job_pub_sub.listen.return_value = [{'data': 'test'}]
            worker = Worker(None, None)
            worker.instance = 'some'
            cleaner.get_worker = mock.MagicMock()
            cleaner.get_worker.return_value = 'id', worker
            cleaner.client = mock.MagicMock()
            cleaner.client.exists.return_value = True
            cleaner.client.get.return_value = pickle.dumps(Job('finished', 'something'))
            cleaner.settings = mock.MagicMock()
            cleaner.settings.recycle_workers = False

            cleaner.run()

            assert cleaner.client.exists.call_count == 1
            assert cleaner.client.get.call_count == 1
            assert worker_mock.call_count == 1

    @mock.patch('consuela.Consuela.__init__', mock.Mock(return_value=None))
    def test_no_job_machine_removal(self):
        from consuela import Consuela
        from worker import Worker

        with mock.patch('consuela.terminate_worker') as worker_mock:

            cleaner = Consuela()
            cleaner.job_pub_sub = mock.MagicMock()
            cleaner.job_pub_sub.listen.return_value = [{'data': 'test'}]
            worker = Worker(None, None)
            worker.instance = 'some'
            cleaner.get_worker = mock.MagicMock()
            cleaner.get_worker.return_value = 'id', worker
            cleaner.client = mock.MagicMock()
            cleaner.client.exists.return_value = False

            cleaner.run()

            assert cleaner.client.exists.call_count == 1
            assert worker_mock.call_count == 1

    @mock.patch('consuela.Consuela.__init__', mock.Mock(return_value=None))
    def test_normal_machine_recycle(self):
        from consuela import Consuela
        from job import Job
        from worker import Worker

        cleaner = Consuela()
        cleaner.job_pub_sub = mock.MagicMock()
        cleaner.job_pub_sub.listen.return_value = [{'data': 'test'}]
        worker = Worker(None, None)
        worker.instance = 'some'
        cleaner.get_worker = mock.MagicMock()
        cleaner.get_worker.return_value = 'id', worker
        cleaner.client = mock.MagicMock()
        cleaner.client.exists.return_value = True
        cleaner.client.get.return_value = pickle.dumps(Job('finished', 'something'))
        cleaner.settings = mock.MagicMock()
        cleaner.settings.recycle_workers = True
        cleaner.recycle_worker = mock.MagicMock()
        cleaner.recycle_worker.return_value = True

        cleaner.run()

        assert cleaner.client.exists.call_count == 1
        assert cleaner.client.get.call_count == 1
        assert pickle.loads(cleaner.client.set.call_args_list[0][0][1]).job_id is None

    @mock.patch('consuela.Consuela.__init__', mock.Mock(return_value=None))
    def test_no_job_machine_recycle_removal(self):
        from consuela import Consuela
        from job import Job
        from worker import Worker

        with mock.patch('consuela.terminate_worker') as worker_mock:

            cleaner = Consuela()
            cleaner.job_pub_sub = mock.MagicMock()
            cleaner.job_pub_sub.listen.return_value = [{'data': 'test'}]
            worker = Worker(None, None)
            worker.instance = 'some'
            cleaner.get_worker = mock.MagicMock()
            cleaner.get_worker.return_value = 'id', worker
            cleaner.client = mock.MagicMock()
            cleaner.client.exists.return_value = True
            cleaner.client.get.return_value = pickle.dumps(Job('finished', 'something'))
            cleaner.settings = mock.MagicMock()
            cleaner.settings.recycle_workers = True
            cleaner.recycle_worker = mock.MagicMock()
            cleaner.recycle_worker.return_value = False

            cleaner.run()

            assert cleaner.client.exists.call_count == 1
            assert worker_mock.call_count == 1

    @mock.patch('consuela.Consuela.__init__', mock.Mock(return_value=None))
    def test_failed_job_machine_removal(self):
        from consuela import Consuela
        from job import Job
        from worker import Worker

        with mock.patch('consuela.terminate_worker') as worker_mock:

            cleaner = Consuela()
            cleaner.job_pub_sub = mock.MagicMock()
            cleaner.job_pub_sub.listen.return_value = [{'data': 'test'}]
            worker = Worker(None, None)
            worker.instance = 'some'
            cleaner.get_worker = mock.MagicMock()
            cleaner.get_worker.return_value = 'id', worker
            cleaner.client = mock.MagicMock()
            cleaner.client.exists.return_value = True
            cleaner.client.get.return_value = pickle.dumps(Job('failed', 'something'))
            cleaner.settings = mock.MagicMock()
            cleaner.settings.recycle_workers = True
            cleaner.recycle_worker = mock.MagicMock()
            cleaner.recycle_worker.return_value = False

            cleaner.run()

            assert cleaner.client.exists.call_count == 1
            assert worker_mock.call_count == 1


if __name__ == '__main__':
    unittest.main()
