import requests
import json
import optparse
import sys


def test_process_graph_in_pull_request(address):
  pr_data = {"user" : "mmcguinn",
             "repo" : "iSENSE-Hardware",
             "commitHashes" : ["0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad"],
             "modifiedFiles" : [],
             "pullRequestId" : 1}
  expected = [{"className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", "error": "", "fileName": "RestAPIDbAdapter.java", "id": 1, "line": 405, "methodName": "getExperiments", "packageName": "edu.uml.cs.droidsense.comm"}, {"className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", "error": "", "fileName": "RestAPIDbAdapter.java", "id": 2, "line": 405, "methodName": "getExperiments", "packageName": "edu.uml.cs.droidsense.comm"}, {"className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", "error": "", "fileName": "RestAPIDbAdapter.java", "id": 3, "line": 405, "methodName": "getExperiments", "packageName": "edu.uml.cs.droidsense.comm"}, {"className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", "error": "", "fileName": "RestAPIDbAdapter.java", "id": 4, "line": 405, "methodName": "getExperiments", "packageName": "edu.uml.cs.droidsense.comm"}, {"className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", "error": "", "fileName": "RestAPIDbAdapter.java", "id": 5, "line": 405, "methodName": "getExperiments", "packageName": "edu.uml.cs.droidsense.comm"}, {"className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", "error": "", "fileName": "RestAPIDbAdapter.java", "id": 6, "line": 405, "methodName": "getExperiments", "packageName": "edu.uml.cs.droidsense.comm"}, {"className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", "error": "", "fileName": "RestAPIDbAdapter.java", "id": 7, "line": 405, "methodName": "getExperiments", "packageName": "edu.uml.cs.droidsense.comm"}]

  try:
    r = requests.post("http://%s/process_graphs_in_pull_request" % address,
                      json=pr_data)

  except Exception as e:
    print(str(e))
    raise

  assert r.status_code == 200

  cmp1 = json.dumps(r.json(), sort_keys=True)
  cmp2 = json.dumps(expected, sort_keys=True)

  if (cmp1 != cmp2):
    raise Exception("Wrong result!")

  return 0


def test_inspect_anomaly(address):
  user_name = "mmcguinn"
  repo_name = "iSENSE-Hardware"
  commit_hash = "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad"
  pr_id = 1
  anomaly_id = "1"

  service_input = {
    "anomalyId" : str(),
    "pullRequest" : {"user" : user_name, "repo" : repo_name,
                     "id" : str(pr_id)}
  }

  expected_output = {
    "editText" : "",
    "fileName" : "RestAPIDbAdapter.java",
    "lineNumber" : 405
  }

  try:
    r = requests.post("http://%s/inspect_anomaly" % address, json=service_input)
  except Exception as e:
    print(str(e))
    raise
  assert r.status_code == 200

  cmp1 = json.dumps(r.json(), sort_keys=True)
  cmp2 = json.dumps(expected_output, sort_keys=True)
  if (cmp1 != cmp2):
    raise Exception("Wrong result!")

  return 0

def test_explain_anomaly(address):
  user_name = "mmcguinn"
  repo_name = "iSENSE-Hardware"
  commit_hash = "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad"
  pr_id = 1
  anomaly_id = "1"

  service_input = {
    "anomalyId" : str(),
    "pullRequest" : {"user" : user_name, "repo" : repo_name,
                     "id" : str(pr_id)}
  }

  expected_output = {
    "patternCode" : "",
    "numberOfExamples" : 1
  }

  try:
    r = requests.post("http://%s/explain_anomaly" % address, json=service_input)
  except Exception as e:
    print(str(e))
    raise
  assert r.status_code == 200

  cmp1 = json.dumps(r.json(), sort_keys=True)
  cmp2 = json.dumps(expected_output, sort_keys=True)
  if (cmp1 != cmp2):
    raise Exception("Wrong result!")

  return 0




p = optparse.OptionParser()
p.add_option('-a', '--address', help="Ip address of the solr server")
p.add_option('-p', '--port', help="Port of the solr server")

opts, args = p.parse_args()
if (not opts.address):
    print "Server address not provided! (try localhost)"
    sys.exit(1)

if (not opts.port):
    print "Server port not provided! (try 30072)"
    sys.exit(1)

address="%s:%s" % (opts.address, opts.port)

test_process_graph_in_pull_request(address)
test_inspect_anomaly(address)
test_explain_anomaly(address)

print "All is ok!"
