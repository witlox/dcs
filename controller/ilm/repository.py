import logging

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from ..settings import Settings


class AmiRepository():
    def __init__(self, collection=None):
        settings = Settings('ILM-AMIs')
        if collection is None:
            collection = "amis"
        try:
            self.client = MongoClient(settings.mongo_url, settings.mongo_port)
        except ConnectionFailure(str):
            logging.error("Cannot connect with the MongoDB server: " + str)
            raise
        self.amis = self.client.ilm[collection]

    def get_all_amis(self):
        all_amis = []
        amis_cursor = self.amis.find()
        for ami in amis_cursor:
            all_amis.append(ami.name)
        return all_amis

    def insert_ami(self, ami, credentials):
        ami_id = str(self.amis.insert({'name': ami, 'credentials': credentials}))
        return ami_id

    def delete_ami(self, name):
        amis_cursor = self.amis.find()
        for ami in amis_cursor:
            if ami.name == name:
                return self.amis.remove(ami)
        return None