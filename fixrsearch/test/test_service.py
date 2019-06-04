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


from fixrsearch.search_service import create_app, DB

from fixrsearch.utils import (
  RepoRef,
  PullRequestRef,
  CommitRef
)

try:
  import unittest2 as unittest
except ImportError:
  import unittest

from fixrsearch.index import IndexNode, ClusterIndex
import fixrsearch

class TestServices(unittest.TestCase):
  def __init__(self, *args, **kwargs):
    super(TestServices, self).__init__(*args, **kwargs)

    self.app = None
    self.test_client = None
    self.test_path = None
    self.data_path = None
    self.graph_path = None
    self.cluster_path = None

  def setUp(self):
    # Builds the path to find the test data
    self.test_path = os.path.dirname(fixrsearch.test.__file__)
    self.data_path = os.path.join(self.test_path, "data")
    assert os.path.isdir(self.data_path)
    self.graph_path = os.path.join(self.data_path, "graphs")
    self.cluster_path = os.path.join(self.data_path, "clusters")

    assert os.path.isdir(self.graph_path)
    assert os.path.isdir(self.cluster_path)

    # Build the path to the graph iso repository
    # Assume to have it in "../../../FixrGraphIso/"
    self.base_iso_path = os.path.join(self.test_path, "../../../FixrGraphIso")
    self.base_iso_path = os.path.abspath(self.base_iso_path)
    assert os.path.isdir(self.base_iso_path)

    self.iso_bin_path = os.path.join(self.base_iso_path,
                                         "build/src/fixrgraphiso/searchlattice")
    assert os.path.isfile(self.iso_bin_path)

    self.app = create_app(self.graph_path,
                          self.cluster_path,
                          self.iso_bin_path)
    self.app.testing = True
    self.test_client = self.app.test_client()

  def tearDown(self):
    index_file = os.path.join(self.graph_path, "graph_index.json")
    if (os.path.exists(index_file)):
      os.remove(index_file)

  def test_search(self):
    key = "%s/%s/%s/%s/%s" % ("dfredriksen",
                              "stealthmessenger",
                              "d6612b984e9c2eca48bdd73fc7d0d29c242207ff",
                              "com.ninjitsuware.notepad.NotesDbAdapter.fetchNote",
                              "161")

    data = {"groum_key" : key}
    response = self.test_client.post('/search',
                                     data=json.dumps(data),
                                     content_type='application/json')
    json_data = json.loads(response.get_data(as_text=True))

    assert json_data['status'] == 0
    assert len(json_data['results']) > 0

    found = False
    all_results = json_data['results']
    for search_results in all_results:
      for res in search_results['search_results']:

        if 'popular' in res:
          elem = res['popular']
          if (elem['type'] == 'popular' and
              elem['frequency'] == 48):
            found = True
            break

    self.assertTrue(found)

  def test_get_apps(self):
    data = {}

    assert not self.test_client is None

    response = self.test_client.get('/get_apps',
                                    data=json.dumps(data),
                                    content_type='application/json')
    json_data = json.loads(response.get_data(as_text=True))

    # Number of apps in the dataset
    self.assertTrue(3 == len(json_data))

    found = False
    for repo in json_data:
      if (repo["user_name"] == u'nadafigment' and
          repo["repo_name"] == u'samples' and
          repo["commit_hash"] == u'5aaee46bb69a1e20ed8a7c97c1a8323dba76cf17'):
        found = True

    self.assertTrue(found)


  def test_get_groums(self):
    data = {"app_key" : u'nadafigment/samples/5aaee46bb69a1e20ed8a7c97c1a8323dba76cf17'}

    assert not self.test_client is None

    response = self.test_client.post('/get_groums', data=json.dumps(data),
                                     content_type='application/json')
    json_data = json.loads(response.get_data(as_text=True))

    assert 0 < len(json_data)

    found = False
    for groum in json_data:
      if (groum[u'groum_key'] == u'nadafigment/samples/5aaee46bb69a1e20ed8a7c97c1a8323dba76cf17/com.github.nadafigment.samples.nadanote.NadaNote$1.onKey/74' and
          groum[u'method_line_number'] == 74,
          groum[u'package_name'] == u'com.github.nadafigment.samples.nadanote',
          groum[u'class_name'] == u'com.github.nadafigment.samples.nadanote.NadaNote$1',
          groum[u'source_class_name'] == u'NadaNote.java',
          groum[u'method_name'] == u'onKey'):
        found = True

    self.assertTrue(found)


  def test_new_pr(self):
    # pre-populate the db with the pull request data
    # temporary
    user_name = "mmcguinn"
    repo_name = "iSENSE-Hardware"
    commit_hash = "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad"
    pr_id = 1

    repo_ref = RepoRef(repo_name, user_name)
    commit_ref = CommitRef(repo_ref, commit_hash)
    pr_ref = PullRequestRef(repo_ref, pr_id, commit_ref)
    db = self.app.config[DB]
    db.new_pr(pr_ref)

    pull_request_data = {"user" : user_name,
                         "repo" : repo_name,
                         "commitHashes" : [],
                         "modifiedFiles" : [],
                         "pullRequestId" : pr_id}

    response = self.test_client.post('/process_graphs_in_pull_request',
                                     data=json.dumps(pull_request_data),
                                     content_type='application/json')
    self.assertTrue(200 == response.status_code)

    json_data = json.loads(response.get_data(as_text=True))

    self.assertTrue(len(json_data) > 0)
