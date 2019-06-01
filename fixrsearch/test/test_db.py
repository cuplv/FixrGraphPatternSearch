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
from fixrsearch.utils import (
  RepoReference, CommitReference,
  PullRequestReference,
  MethodReference,
  Pattern)

try:
    import unittest2 as unittest
except ImportError:
    import unittest

class TestDbNew(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestDbNew, self).__init__(*args, **kwargs)

    def test_creation(self):
        config = SQLiteConfig(TestDb.DB_NAME)
        db = Db(config)    
        db.connect_or_create()
        db.disconnect()
        os.remove(TestDb.DB_NAME)

class TestDb(unittest.TestCase):
    DB_NAME = "/tmp/testDB.sqlite"

    def __init__(self, *args, **kwargs):
        super(TestDb, self).__init__(*args, **kwargs)
        self.db = None

    def setUp(self):
        config = SQLiteConfig(TestDb.DB_NAME)
        self.db = Db(config)    
        self.db.connect_or_create()


    def testInsertRepo(self):
        user_name = "cuplv"
        repo_name = "biggroum"

        repo = RepoReference(repo_name, user_name)
        self.db.new_repo(repo)

        res = self.db.get_repo(repo)
        self.assertIsNotNone(res)
        (res_id, repo1) = res
        self.assertEquals(repo, repo1)

    def testInsertCommit(self):
        user_name = "cuplv"
        repo_name = "biggroum"
        commit_hash = "f0cc7668ba469c920c581536f2f364b47c91d075"

        commit_ref = CommitReference(RepoReference(repo_name, user_name),
                                     commit_hash)
        res = self.db.new_commit(commit_ref)
        (res_id, commit) = res
        self.assertEquals(commit_ref, commit)

    def testInsertPullRequest(self):
        user_name = "cuplv"
        repo_name = "biggroum"
        pr_number = 1

        pull_request_ref = PullRequestReference(RepoReference(repo_name, user_name),
                                                pr_number)
        res = self.db.new_pr(pull_request_ref)
        (res_id, pr1) = res
        self.assertEquals(pull_request_ref, pr1)

    def testInsertMethod(self):
      commit_ref = CommitReference(RepoReference("biggroum", "cuplv"),
                                   "f0cc7668ba469c920c581536f2f364b47c91d075")
      data = MethodReference(commit_ref,
                             "MyClass",
                             "edu.colorado.plv",
                             "doSomething",
                             "12",
                             "MyClass.java")

      (res_id, old_data) = self.db.new_method(data)
      self.assertEquals(old_data, data)

    def testInsertPattern(self):
      repo_ref = RepoReference("biggroum", "cuplv")
      data = Pattern(repo_ref, "5/2/1", "text")

      (res_id, old_data) = self.db.new_pattern(data)
      self.assertEquals(old_data, data)


    def tearDown(self):
        self.db.disconnect()
        os.remove(TestDb.DB_NAME)



        



