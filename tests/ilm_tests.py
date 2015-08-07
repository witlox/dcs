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

    @mock.patch('repository.AmiRepository.__init__', mock.Mock(return_value=None))
    def test_normal_machine_state_flow_for_requested(self):
        self.aws_mock.start_machine = mock.MagicMock()
        self.aws_mock.start_machine.return_value = 'jm-', 'res0'

        from repository import AmiRepository
        from worker import Worker
        from job import Job

        repository = AmiRepository()
        repository.client = mock.MagicMock()
        repository.client.exists.return_value = True
        job = Job('received', 'something')
        repository.client.get.return_value = pickle.dumps(job)
        repository.client.set = mock.MagicMock()
        repository.client.publish = mock.MagicMock()
        repository.job_changed('test')

        assert repository.client.exists.call_count == 1
        assert len(repository.client.set.call_args_list) == 2
        assert repository.client.set.call_args_list[0][0][0] == 'jm-'
        assert repository.client.set.call_args_list[1][0][0] == 'test'
        assert repository.client.publish.call_count == 1
        assert pickle.loads(repository.client.set.call_args_list[1][0][1]).state == 'requested'

    @mock.patch('repository.AmiRepository.__init__', mock.Mock(return_value=None))
    def test_requestfailed_machine_state_flow_for_requested(self):
        self.aws_mock.start_machine = mock.MagicMock()
        self.aws_mock.start_machine.return_value = None, None

        from repository import AmiRepository
        from worker import Worker
        from job import Job

        repository = AmiRepository()
        repository.client = mock.MagicMock()
        repository.client.exists.return_value = True
        job = Job('received', 'something')
        repository.client.get.return_value = pickle.dumps(job)
        repository.client.set = mock.MagicMock()
        repository.client.publish = mock.MagicMock()
        repository.job_changed('test')

        assert repository.client.exists.call_count == 1
        assert len(repository.client.set.call_args_list) == 1
        assert pickle.loads(repository.client.set.call_args_list[0][0][1]).state == 'ami request failed'
        assert repository.client.publish.call_count == 1

    @mock.patch('repository.AmiRepository.__init__', mock.Mock(return_value=None))
    def test_normal_machine_state_flow_for_delete(self):
        self.aws_mock.check_running = mock.MagicMock()
        self.aws_mock.check_running.return_value = True
        self.aws_mock.terminate_machine = mock.MagicMock()
        self.aws_mock.terminate_machine.return_value = 'some'

        from repository import AmiRepository
        from worker import Worker
        from job import Job

        repository = AmiRepository()
        repository.client = mock.MagicMock()
        repository.client.exists.return_value = False
        repository.client.keys.return_value = ['jm-']
        worker = Worker('test', 'batch-')
        worker.reservation = 'reservation'
        worker.instance = 'instance'
        worker.request_time = datetime.now()
        worker.ip_address = 'something'
        repository.client.get.return_value = pickle.dumps(worker)
        repository.client.delete = mock.MagicMock()
        repository.job_changed('test')

        assert repository.client.exists.call_count == 1
        assert repository.client.keys.call_count == 1
        assert repository.client.get.call_count == 1
        assert repository.client.delete.call_count == 1
        assert repository.client.delete.call_args[0][0] == 'jm-'

    @mock.patch('repository.AmiRepository.__init__', mock.Mock(return_value=None))
    def test_invalidjobid_machine_state_flow_for_delete(self):
        self.aws_mock.check_running = mock.MagicMock()
        self.aws_mock.check_running.return_value = True
        self.aws_mock.terminate_machine = mock.MagicMock()

        from repository import AmiRepository
        from worker import Worker
        from job import Job

        repository = AmiRepository()
        repository.client = mock.MagicMock()
        repository.client.exists.return_value = False
        repository.client.keys.return_value = ['jm-']
        worker = Worker('test1', 'batch-')
        worker.reservation = 'reservation'
        worker.instance = 'instance'
        worker.request_time = datetime.now()
        worker.ip_address = 'something'
        repository.client.get.return_value = pickle.dumps(worker)
        repository.client.set = mock.MagicMock()
        repository.job_changed('test')

        assert repository.client.exists.call_count == 1
        assert repository.client.keys.call_count == 1
        assert self.aws_mock.terminate_machine.call_count == 0

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.poky_pokey', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.pull', mock.Mock(return_value=None))
    def test_normal_machinemidwife_flow(self):
        self.aws_mock.my_booted_machine = mock.MagicMock()
        self.aws_mock.my_booted_machine.return_value= 'instance', 'ip'

        from machine_midwife import MachineMidwife
        from worker import Worker
        from job import Job

        midwife = MachineMidwife()
        midwife.client = mock.MagicMock()
        midwife.client.keys.return_value = ['jm-']
        midwife.settings = mock.MagicMock()
        midwife.settings.aws_req_max_wait = 15
        worker = Worker('jm-', 'batch-')
        worker.reservation = 'reservation'
        worker.instance = None
        worker.request_time = datetime.now()
        worker.ip_address = None
        midwife.client.get.side_effect = [pickle.dumps(worker), pickle.dumps(Job('requested', 'something'))]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.check_newborn()

        assert midwife.client.keys.call_count == 1
        assert midwife.client.get.call_count == 2
        assert midwife.client.set.call_count == 2
        assert midwife.client.publish.call_count == 1
        assert self.aws_mock.my_booted_machine.call_count == 1
        assert pickle.loads(midwife.client.set.call_args_list[1][0][1]).state == 'booted'

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.poky_pokey', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.pull', mock.Mock(return_value=None))
    def test_stale_machinemidwife_flow(self):
        self.aws_mock.my_booted_machine = mock.MagicMock()

        from machine_midwife import MachineMidwife
        from worker import Worker
        from job import Job

        midwife = MachineMidwife()
        midwife.client = mock.MagicMock()
        midwife.client.keys.return_value = ['jm-']
        midwife.settings = mock.MagicMock()
        midwife.settings.aws_req_max_wait = 15
        worker = Worker('jm-', 'batch-')
        worker.reservation = 'reservation'
        worker.instance = None
        worker.request_time = datetime.now()-timedelta(hours=1, milliseconds=1)
        worker.ip_address = None
        midwife.client.get.side_effect = [pickle.dumps(worker), pickle.dumps(Job('requested', 'something'))]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.check_newborn()

        assert midwife.client.keys.call_count == 1
        assert midwife.client.get.call_count == 2
        assert midwife.client.set.call_count == 1
        assert midwife.client.publish.call_count == 1
        assert self.aws_mock.my_booted_machine.call_count == 0
        assert pickle.loads(midwife.client.set.call_args_list[0][0][1]).state == 'received'

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.poky_pokey', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.pull', mock.Mock(return_value=None))
    def test_machinemidwife_finished_flow_without_recycle(self):
        self.aws_mock.terminate_machine = mock.MagicMock()
        self.aws_mock.terminate_machine.return_value = 'some'

        from machine_midwife import MachineMidwife
        from worker import Worker
        from job import Job

        midwife = MachineMidwife()
        midwife.settings = mock.MagicMock()
        midwife.settings.aws_req_max_wait = 15
        midwife.settings.recycle_workers = False
        midwife.client = mock.MagicMock()
        midwife.client.keys.return_value = ['jm-']
        worker = Worker('jm-','batch-')
        worker.reservation = 'reservation'
        worker.instance = 'instance'
        worker.ip_address = None
        midwife.client.get.side_effect = [pickle.dumps(worker), pickle.dumps(Job('finished', 'something'))]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.check_newborn()

        assert midwife.client.keys.call_count == 1
        assert midwife.client.get.call_count == 2
        assert self.aws_mock.terminate_machine.call_count == 1

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.poky_pokey', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.pull', mock.Mock(return_value=None))
    def test_machinemidwife_finished_flow_with_recycle_with_spawn(self):
        self.aws_mock.terminate_machine = mock.MagicMock()
        self.aws_mock.terminate_machine.return_value = 'some'

        from machine_midwife import MachineMidwife
        from worker import Worker
        from job import Job

        midwife = MachineMidwife()
        midwife.settings = mock.MagicMock()
        midwife.settings.aws_req_max_wait = 15
        midwife.settings.recycle_workers = True
        midwife.client = mock.MagicMock()
        midwife.client.keys.return_value = ['jm-']
        worker = Worker('jm-', 'batch-')
        worker.reservation = 'reservation'
        worker.instance = 'instance'
        worker.ip_address = None
        job = Job('spawned', 'batch-')
        midwife.client.get.side_effect = [pickle.dumps(worker), pickle.dumps(Job('finished', 'batch-')), pickle.dumps(job)]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.check_newborn()

        assert midwife.client.keys.call_count == 2
        assert midwife.client.get.call_count == 3
        assert self.aws_mock.terminate_machine.call_count == 0

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.poky_pokey', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.pull', mock.Mock(return_value=None))
    def test_machinemidwife_finished_flow_with_recycle_without_spawn(self):
        self.aws_mock.terminate_machine = mock.MagicMock()
        self.aws_mock.terminate_machine.return_value = 'some'

        from machine_midwife import MachineMidwife
        from worker import Worker
        from job import Job

        midwife = MachineMidwife()
        midwife.settings = mock.MagicMock()
        midwife.settings.aws_req_max_wait = 15
        midwife.settings.recycle_workers = True
        midwife.client = mock.MagicMock()
        midwife.client.keys.return_value = ['jm-']
        worker = Worker('jm-', 'batch-')
        worker.reservation = 'reservation'
        worker.instance = 'instance'
        worker.ip_address = None
        job = Job('happy', 'batch-')
        midwife.client.get.side_effect = [pickle.dumps(worker), pickle.dumps(Job('finished', 'batch-')), pickle.dumps(job)]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.check_newborn()

        assert midwife.client.keys.call_count == 2
        assert midwife.client.get.call_count == 3
        assert self.aws_mock.terminate_machine.call_count == 1

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.poky_pokey', mock.Mock(return_value=None))
    @mock.patch('machine_midwife.MachineMidwife.pull', mock.Mock(return_value=None))
    def test_machinemidwife_failed_without_cleanup_flow(self):
        self.aws_mock.terminate_machine = mock.MagicMock()
        self.aws_mock.terminate_machine.return_value = 'some'

        from machine_midwife import MachineMidwife
        from worker import Worker
        from job import Job

        midwife = MachineMidwife()
        midwife.settings = mock.MagicMock()
        midwife.settings.aws_req_max_wait = 15
        midwife.settings.auto_remove_failed = False
        midwife.client = mock.MagicMock()
        midwife.client.keys.return_value = ['jm-']
        worker = Worker('jm-', 'batch-')
        worker.reservation = 'reservation'
        worker.instance = 'instance'
        worker.ip_address = None
        midwife.client.get.side_effect = [pickle.dumps(worker), pickle.dumps(Job('failed', 'something')), pickle.dumps(['test', 'aaa'])]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.check_newborn()

        assert midwife.client.keys.call_count == 1
        assert midwife.client.get.call_count == 2
        assert self.aws_mock.terminate_machine.call_count == 0

if __name__ == '__main__':
    unittest.main()
