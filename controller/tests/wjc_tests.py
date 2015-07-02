import unittest
import json
import mock

# don't want to create packages
import sys
sys.path.append('../wjc')

from api import api
from repository import JobRepository

class TestIlmApi(unittest.TestCase):
    def setUp(self):
        with mock.patch('repository.MongoClient') as mc:
            self.repository = JobRepository()
            api.config['REPOSITORY'] = self.repository

    def test_get_jobs(self):
        # Arrange
        self.app = api.test_client()

        # Act
        data = {'name': 'test', 'ami': 'test', 'instance_type': 'test'}
        rv1 = self.app.post('/jobs', data=json.dumps(data))
        # Assert
        body1 = rv1.data.decode(rv1.charset)
        self.assertIsNotNone(json.loads(body1))
        # Checks

        # Act
        rv2 = self.app.get('/jobs')
        # Assert
        body2 = rv2.data.decode(rv2.charset)
        self.assertIsNotNone(json.loads(body2))

    def test_received_job_results_in_ilm_request(self):
        # Arrange
        self.app = api.test_client()

        # Act
        data = {'name': 'test', 'ami': 'test', 'instance_type': 'test'}
        rv1 = self.app.post('/jobs', data=json.dumps(data))
        # Assert
        body1 = rv1.data.decode(rv1.charset)
        self.assertIsNotNone(json.loads(body1))
        # Checks




if __name__ == '__main__':
    unittest.main()
