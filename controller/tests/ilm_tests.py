import unittest
import json
import mock

# don't want to create packages
import sys
sys.path.append('../ilm')

from api import api
from repository import AmiRepository

class TestIlmApi(unittest.TestCase):
    def setUp(self):
        with mock.patch('repository.MongoClient') as mc:
            self.repository = AmiRepository()
            api.config['REPOSITORY'] = self.repository

    def test_get_amis(self):
        # Arrange
        self.app = api.test_client()

        # Act
        data = {'name': 'test', 'credentials': {'username': 'test', 'password': 'test'}}
        rv1 = self.app.post('/amis', data=json.dumps(data))
        # Assert
        body1 = rv1.data.decode(rv1.charset)
        self.assertIsNotNone(json.loads(body1))
        # Checks

        # Act
        rv2 = self.app.get('/amis')
        # Assert
        body2 = rv2.data.decode(rv2.charset)
        self.assertIsNotNone(json.loads(body2))


if __name__ == '__main__':
    unittest.main()
