"""
Test the invocation of the web services

"""

import os
import sys
import logging
import requests
import json
import optparse
import httplib


from fixrsearch.db import Db, SQLiteConfig

try:
    import unittest2 as unittest
except ImportError:
    import unittest

class TestDb(unittest.TestCase):
    DB_NAME = "/tmp/testDB.sqlite"

    def __init__(self, *args, **kwargs):
        super(TestDb, self).__init__(*args, **kwargs)

        self.app = None
        self.test_client = None
        self.test_path = None

    def setUp(self):
        # Set up the test
        pass

    def tearDown(self):
        # Builds the path to find the test data
        pass

    def test_creation(self):
        config = SQLiteConfig(TestDb.DB_NAME)
        db = Db(config)    
        db.connect_or_create()
        db.disconnect()


        



