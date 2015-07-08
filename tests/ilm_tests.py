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

        repository = AmiRepository()
        repository.client = mock.MagicMock()
        repository.client.exists.return_value = True
        repository.client.get.return_value = pickle.dumps([None, None, 'received'])
        repository.client.set = mock.MagicMock()
        repository.client.publish = mock.MagicMock()
        repository.job_changed('test')

        assert repository.client.exists.call_count == 1
        assert len(repository.client.set.call_args_list) == 2
        assert repository.client.set.call_args_list[0][0][0] == 'jm-'
        assert repository.client.set.call_args_list[1][0][0] == 'test'
        assert repository.client.publish.call_count == 1
        assert pickle.loads(repository.client.set.call_args_list[0][0][1])[3] == 'requested'
        assert pickle.loads(repository.client.set.call_args_list[1][0][1])[2] == 'requested'

    @mock.patch('repository.AmiRepository.__init__', mock.Mock(return_value=None))
    def test_requestfailed_machine_state_flow_for_requested(self):
        self.aws_mock.start_machine = mock.MagicMock()
        self.aws_mock.start_machine.return_value = None, None

        from repository import AmiRepository

        repository = AmiRepository()
        repository.client = mock.MagicMock()
        repository.client.exists.return_value = True
        repository.client.get.return_value = pickle.dumps([None, None, 'received'])
        repository.client.set = mock.MagicMock()
        repository.client.publish = mock.MagicMock()
        repository.job_changed('test')

        assert repository.client.exists.call_count == 1
        assert len(repository.client.set.call_args_list) == 1
        assert pickle.loads(repository.client.set.call_args_list[0][0][1])[2] == 'ami request failed'
        assert repository.client.publish.call_count == 1

    @mock.patch('repository.AmiRepository.__init__', mock.Mock(return_value=None))
    def test_normal_machine_state_flow_for_delete(self):
        self.aws_mock.terminate_machine = mock.MagicMock()
        self.aws_mock.terminate_machine.return_value = 'some'

        from repository import AmiRepository

        repository = AmiRepository()
        repository.client = mock.MagicMock()
        repository.client.exists.return_value = False
        repository.client.keys.return_value = ['jm-']
        repository.client.get.return_value = pickle.dumps(['test', None, 'instance', 'somthing', None])
        repository.client.delete = mock.MagicMock()
        repository.job_changed('test')

        assert repository.client.exists.call_count == 1
        assert repository.client.keys.call_count == 1
        assert repository.client.get.call_count == 1
        assert repository.client.delete.call_count == 1
        assert repository.client.delete.call_args[0][0] == 'jm-'

    @mock.patch('repository.AmiRepository.__init__', mock.Mock(return_value=None))
    def test_terminatefailed_machine_state_flow_for_delete(self):
        self.aws_mock.terminate_machine = mock.MagicMock()
        self.aws_mock.terminate_machine.return_value = None

        from repository import AmiRepository

        repository = AmiRepository()
        repository.client = mock.MagicMock()
        repository.client.exists.return_value = False
        repository.client.keys.return_value = ['jm-']
        repository.client.get.return_value = pickle.dumps(['test', None, 'instance', 'somthing', None])
        repository.client.set = mock.MagicMock()
        repository.job_changed('test')

        assert repository.client.exists.call_count == 1
        assert repository.client.keys.call_count == 1
        assert repository.client.get.call_count == 1
        assert repository.client.set.call_count == 1
        assert pickle.loads(repository.client.set.call_args_list[0][0][1])[3] == 'terminate failed'

    @mock.patch('repository.AmiRepository.__init__', mock.Mock(return_value=None))
    def test_invalidjobid_machine_state_flow_for_delete(self):
        self.aws_mock.terminate_machine = mock.MagicMock()

        from repository import AmiRepository

        repository = AmiRepository()
        repository.client = mock.MagicMock()
        repository.client.exists.return_value = False
        repository.client.keys.return_value = ['jm-']
        repository.client.get.return_value = pickle.dumps(['test1', None, 'instance', 'somthing', None])
        repository.client.set = mock.MagicMock()
        repository.job_changed('test')

        assert repository.client.exists.call_count == 1
        assert repository.client.keys.call_count == 1
        assert self.aws_mock.terminate_machine.call_count == 0

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    def test_normal_machinemidwife_flow(self):
        self.aws_mock.my_booted_machine = mock.MagicMock()
        self.aws_mock.my_booted_machine.return_value= 'instance', 'ip'

        from machine_midwife import MachineMidwife

        midwife = MachineMidwife()
        midwife.client = mock.MagicMock()
        midwife.client.keys.return_value = ['jm-']
        midwife.client.get.side_effect = [pickle.dumps(['test1', 'some', None, 'requested', datetime.now()]), pickle.dumps([None, None, None])]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.check_newborn()

        assert midwife.client.keys.call_count == 1
        assert midwife.client.get.call_count == 2
        assert midwife.client.set.call_count == 2
        assert midwife.client.publish.call_count == 1
        assert self.aws_mock.my_booted_machine.call_count == 1
        assert pickle.loads(midwife.client.set.call_args_list[0][0][1])[3] == 'booted'
        assert pickle.loads(midwife.client.set.call_args_list[1][0][1])[2] == 'booted'

    @mock.patch('machine_midwife.MachineMidwife.__init__', mock.Mock(return_value=None))
    def test_stale_machinemidwife_flow(self):
        self.aws_mock.my_booted_machine = mock.MagicMock()

        from machine_midwife import MachineMidwife

        midwife = MachineMidwife()
        midwife.client = mock.MagicMock()
        midwife.client.keys.return_value = ['jm-']
        midwife.client.get.side_effect = [pickle.dumps(['test1', 'some', None, 'requested', datetime.now()-timedelta(hours=1, milliseconds=1)]), pickle.dumps([None, None, None])]
        midwife.client.set = mock.MagicMock()
        midwife.client.publish = mock.MagicMock()

        midwife.check_newborn()

        assert midwife.client.keys.call_count == 1
        assert midwife.client.get.call_count == 2
        assert midwife.client.set.call_count == 2
        assert midwife.client.publish.call_count == 1
        assert self.aws_mock.my_booted_machine.call_count == 0
        assert pickle.loads(midwife.client.set.call_args_list[0][0][1])[3] == 'request failed'
        assert pickle.loads(midwife.client.set.call_args_list[1][0][1])[2] == 'boot failed'



if __name__ == '__main__':
    unittest.main()
