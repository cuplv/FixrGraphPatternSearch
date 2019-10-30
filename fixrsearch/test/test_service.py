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


from fixrsearch.search_service import create_app, get_new_db, DB_CONFIG

from fixrsearch.anomaly import Anomaly 

from fixrsearch.utils import (
  RepoRef,
  PullRequestRef,
  CommitRef,
  MethodRef,
  ClusterRef,
  PatternRef
)

try:
  import unittest2 as unittest
except ImportError:
  import unittest

from fixrsearch.index import IndexNode, ClusterIndex
import fixrsearch

class TestServices(unittest.TestCase):
  DB_PATH = "/tmp/service_db.db"

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
                          self.iso_bin_path,
                          TestServices.DB_PATH,
                          "localhost",
                          "8080")
    self.app.testing = True
    self.test_client = self.app.test_client()

  def tearDown(self):
    index_file = os.path.join(self.graph_path, "graph_index.json")
    if (os.path.exists(index_file)):
      os.remove(index_file)

    if (os.path.exists(TestServices.DB_PATH)):
      os.remove(TestServices.DB_PATH)


  def test_search(self):
    user_name = "mmcguinn"
    repo_name = "iSENSE-Hardware"
    commit_hash = "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad"

    # key = "%s/%s/%s/%s/%s" % ("dfredriksen",
    #                           "stealthmessenger",
    #                           "d6612b984e9c2eca48bdd73fc7d0d29c242207ff",
    #                           "com.ninjitsuware.notepad.NotesDbAdapter.fetchNote",
    #                           "161")

    key = "%s/%s/%s/%s/%s" % (user_name,
                              repo_name,
                              commit_hash,
                              "edu.uml.cs.droidsense.comm.RestAPIDbAdapter.getExperiments",
                              405)


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
              elem['frequency'] == 72):
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
    self.assertTrue(5 <= len(json_data))

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


  def test_process_graphs_in_pull_request(self):
    user_name = "mmcguinn"
    repo_name = "iSENSE-Hardware"
    commit_hash = "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad"
    pr_id = 1
    repo_ref = RepoRef(repo_name, user_name)
    commit_ref = CommitRef(repo_ref, commit_hash)
    pr_ref = PullRequestRef(repo_ref, pr_id, commit_ref)

    commit_hash_data = {"data" : [{"sha" : commit_hash}]}

    pull_request_data = {"user" : user_name,
                         "repo" : repo_name,
                         "commitHashes" : commit_hash_data,
                         "modifiedFiles" : [],
                         "pullRequestId" : pr_id}

    response = self.test_client.post('/process_graphs_in_pull_request',
                                     data=json.dumps(pull_request_data),
                                     content_type='application/json')
    self.assertTrue(200 == response.status_code)

    json_data = json.loads(response.get_data(as_text=True))

    self.assertTrue(len(json_data) > 0)

  def test_process_graphs_in_pull_request_2(self):
    user_name = "DevelopFreedom"
    repo_name = "logmein-android"
    commit_hash = "418b37ffbafac3502b661d0918d1bc190e3c2dd1"
    pr_id = 1

    repo_ref = RepoRef(repo_name, user_name)
    commit_ref = CommitRef(repo_ref, commit_hash)
    pr_ref = PullRequestRef(repo_ref, pr_id, commit_ref)

    commit_hash_data = {"data" : [{"sha" : commit_hash}]}

    pull_request_data = {"user" : user_name,
                         "repo" : repo_name,
                         "commitHashes" : commit_hash_data,
                         "modifiedFiles" : [],
                         "pullRequestId" : pr_id}

    response = self.test_client.post('/process_graphs_in_pull_request',
                                     data=json.dumps(pull_request_data),
                                     content_type='application/json')
    self.assertTrue(200 == response.status_code)

    json_data = json.loads(response.get_data(as_text=True))

    self.assertTrue(len(json_data) > 0)

  def test_process_graphs_in_pull_request_3(self):
    user_name = "smover"
    repo_name = "AwesomeApp"
    commit_hash = "04f68b69a6f9fa254661b481a757fa1c834b52e1"
    pr_id = 1

    repo_ref = RepoRef(repo_name, user_name)
    commit_ref = CommitRef(repo_ref, commit_hash)
    pr_ref = PullRequestRef(repo_ref, pr_id, commit_ref)

    commit_hash_data = {"data" : [{"sha" : commit_hash}]}

    pull_request_data = {"user" : user_name,
                         "repo" : repo_name,
                         "commitHashes" : commit_hash_data,
                         "modifiedFiles" : [],
                         "pullRequestId" : pr_id}

    response = self.test_client.post('/process_graphs_in_pull_request',
                                     data=json.dumps(pull_request_data),
                                     content_type='application/json')
    self.assertTrue(200 == response.status_code)

    json_data = json.loads(response.get_data(as_text=True))

    # At least some result
    self.assertTrue(len(json_data) > 0)

    # Compare with the expected output
    expected_output = [
      {
        u'methodName': u'showDialog',
        u'packageName': u'fixr.plv.colorado.edu.awesomeapp',
        u'fileName': u'[MainActivity.java](https://github.com/smover/AwesomeApp/blob/04f68b69a6f9fa254661b481a757fa1c834b52e1/app/src/main/java/fixr/plv/colorado/edu/awesomeapp/MainActivity.java)',
        u'className': u'fixr.plv.colorado.edu.awesomeapp.MainActivity',
        u'error': u'missing method calls',
        u'line': 47,
        u'id': 1
      },
      {u'methodName': u'showDialog',
       u'packageName': u'fixr.plv.colorado.edu.awesomeapp',
       u'fileName': u'[MainActivity.java](https://github.com/smover/AwesomeApp/blob/04f68b69a6f9fa254661b481a757fa1c834b52e1/app/src/main/java/fixr/plv/colorado/edu/awesomeapp/MainActivity.java)',
       u'className': u'fixr.plv.colorado.edu.awesomeapp.MainActivity',
      u'error': u'missing method calls',
       u'line': 47,
       u'id': 2
      }
    ]

    self.assertTrue(json.dumps(json_data, sort_keys=True) ==
                    json.dumps(expected_output, sort_keys=True))



  def get_anomaly(self):
    user_name = "mmcguinn"
    repo_name = "iSENSE-Hardware"
    commit_hash = "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad"
    pr_id = 1
    anomaly_id = "1"
    description = ""
    patch_text = ""
    pattern_anomaly_text = ""

    repo_ref = RepoRef(repo_name, user_name)
    commit_ref = CommitRef(repo_ref, commit_hash)

    anomaly = Anomaly(anomaly_id,
                      MethodRef(commit_ref,
                                "RestAPIDbAdapter",
                                "edu.uml.cs.droidsense.comm",
                                "getExperiments",
                                405,
                                "RestAPIDbAdapter.java"),
                      PullRequestRef(repo_ref,
                                     pr_id,
                                     commit_ref),
                      description,
                      patch_text,
                      pattern_anomaly_text,
                      PatternRef(ClusterRef("1", ""), "",
                                 PatternRef.Type.POPULAR, 1.0, 1.0),
                      "iSENSE Mobile/src/edu/uml/cs/droidsense/comm/RestAPI.java"
    )

    db = get_new_db(self.app.config[DB_CONFIG])
    db.new_anomaly(anomaly)
    db.disconnect()

    return anomaly

  def test_inspect_anomaly(self):
    # Prepare the test data
    anomaly = self.get_anomaly()

    service_input = {
      "anomalyId" : str(anomaly.numeric_id),
      "pullRequest" : {"user" : anomaly.pull_request.repo_ref.user_name,
                       "repo" : anomaly.pull_request.repo_ref.repo_name,
                       "id" : str(anomaly.pull_request.number)}
    }

    expected_output = {
      "editText" : "",
      "fileName" : anomaly.git_path,
      "lineNumber" : anomaly.method_ref.start_line_number
    }

    response = self.test_client.post('/inspect_anomaly',
                                     data=json.dumps(service_input),
                                     content_type='application/json')
    self.assertTrue(200 == response.status_code)

    json_data = json.loads(response.get_data(as_text=True))

    self.assertTrue(json.dumps(json_data, sort_keys=True) ==
                    json.dumps(expected_output, sort_keys=True))


  def test_explain_anomaly(self):
    # Prepare the test data
    anomaly = self.get_anomaly()

    service_input = {
      "anomalyId" : str(anomaly.numeric_id),
      "pullRequest" : {"user" : anomaly.pull_request.repo_ref.user_name,
                       "repo" : anomaly.pull_request.repo_ref.repo_name,
                       "id" : str(anomaly.pull_request.number)}
    }

    expected_output = {
      "patternCode" : "",
      "numberOfExamples" : 1.0
    }

    response = self.test_client.post('/explain_anomaly',
                                     data=json.dumps(service_input),
                                     content_type='application/json')
    self.assertTrue(200 == response.status_code)

    json_data = json.loads(response.get_data(as_text=True))

    self.assertTrue(json.dumps(json_data, sort_keys=True) ==
                    json.dumps(expected_output, sort_keys=True))
