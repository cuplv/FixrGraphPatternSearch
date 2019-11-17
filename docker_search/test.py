import requests
import json
import optparse
import sys

def compare(json_obj1, json_obj2):
  cmp1 = json.dumps(json_obj1, sort_keys=True)
  cmp2 = json.dumps(json_obj2, sort_keys=True)

  if (cmp1 != cmp2):
    print(json.dumps(json_obj1, indent=2, sort_keys=True))
    print(json.dumps(json_obj2, indent=2, sort_keys=True))

    raise Exception("Wrong result!")

def test_process_graph_in_pull_request(address):
  commit_hash_data = {"data" : [{"sha" : "0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad"}]}

  pr_data = {"user" : "mmcguinn",
             "repo" : "iSENSE-Hardware",
             "commitHashes" : commit_hash_data,
             "modifiedFiles" : [],
             "pullRequestId" : 1}

  expected = [
    {
      "className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", 
      "error": "missing method calls", 
      "fileName": "[RestAPIDbAdapter.java](https://github.com/mmcguinn/iSENSE-Hardware/blob/0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad/iSENSE Mobile/src/edu/uml/cs/droidsense/comm/RestAPIDbAdapter.java)", 
      "id": 1, 
      "line": 405, 
      "methodName": "getExperiments", 
      "packageName": "edu.uml.cs.droidsense.comm"
    }, 
    {
      "className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", 
      "error": "missing method calls", 
      "fileName": "[RestAPIDbAdapter.java](https://github.com/mmcguinn/iSENSE-Hardware/blob/0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad/iSENSE Mobile/src/edu/uml/cs/droidsense/comm/RestAPIDbAdapter.java)", 
      "id": 2, 
      "line": 405, 
      "methodName": "getExperiments", 
      "packageName": "edu.uml.cs.droidsense.comm"
    }, 
    {
      "className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", 
      "error": "missing method calls", 
      "fileName": "[RestAPIDbAdapter.java](https://github.com/mmcguinn/iSENSE-Hardware/blob/0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad/iSENSE Mobile/src/edu/uml/cs/droidsense/comm/RestAPIDbAdapter.java)", 
      "id": 3, 
      "line": 405, 
      "methodName": "getExperiments", 
      "packageName": "edu.uml.cs.droidsense.comm"
    }, 
    {
      "className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", 
      "error": "missing method calls", 
      "fileName": "[RestAPIDbAdapter.java](https://github.com/mmcguinn/iSENSE-Hardware/blob/0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad/)", 
      "id": 4, 
      "line": 405, 
      "methodName": "getExperiments", 
      "packageName": "edu.uml.cs.droidsense.comm"
    }, 
    {
      "className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", 
      "error": "missing method calls", 
      "fileName": "[RestAPIDbAdapter.java](https://github.com/mmcguinn/iSENSE-Hardware/blob/0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad/iSENSE Mobile/src/edu/uml/cs/droidsense/comm/RestAPIDbAdapter.java)", 
      "id": 5, 
      "line": 405, 
      "methodName": "getExperiments", 
      "packageName": "edu.uml.cs.droidsense.comm"
    }, 
    {
      "className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", 
      "error": "missing method calls", 
      "fileName": "[RestAPIDbAdapter.java](https://github.com/mmcguinn/iSENSE-Hardware/blob/0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad/iSENSE Mobile/src/edu/uml/cs/droidsense/comm/RestAPIDbAdapter.java)", 
      "id": 6, 
      "line": 405, 
      "methodName": "getExperiments", 
      "packageName": "edu.uml.cs.droidsense.comm"
    }, 
    {
      "className": "edu.uml.cs.droidsense.comm.RestAPIDbAdapter", 
      "error": "missing method calls", 
      "fileName": "[RestAPIDbAdapter.java](https://github.com/mmcguinn/iSENSE-Hardware/blob/0700782f9d3aa4cb3d4c86c3ccf9dcab13fa3aad/iSENSE Mobile/src/edu/uml/cs/droidsense/comm/RestAPIDbAdapter.java)", 
      "id": 7, 
      "line": 405, 
      "methodName": "getExperiments", 
      "packageName": "edu.uml.cs.droidsense.comm"
    }
  ]

  try:
    endpoint = "http://%s/process_graphs_in_pull_request" % address
    print(endpoint)
    r = requests.post(endpoint, json=pr_data)

  except Exception as e:
    print(str(e))
    raise

  print(r.status_code)
  assert r.status_code == 200

  compare(r.json(), expected)
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
    "editText": "public android.database.Cursor getExperiments(int page, int count) {\n    /* [0] After this method method call (cursor = android.database.sqlite.SQLiteDatabase.rawQuery($r14, query, $r12);\n    )\n    You should invoke the following methods:\n      memberId = android.database.Cursor.getString(cursor, 0);\n      android.database.Cursor.moveToNext(cursor);\n      $z1 = android.database.Cursor.isAfterLast(cursor);\n      android.database.Cursor.close(cursor);\n     */\n    int offset = (page - 1) * count;\n    android.database.Cursor mCursor = mDb.rawQuery(((((((((\"SELECT * FROM \" + (edu.uml.cs.droidsense.comm.RestAPIDbAdapter.DATABASE_TABLE_EXPERIMENTS)) + \" ORDER BY \") + (edu.uml.cs.droidsense.comm.RestAPIDbAdapter.KEY_EXPERIMENT_ID)) + \" DESC\") + \" LIMIT \") + count) + \" OFFSET \") + offset), null);\n    if (mCursor != null) {\n        mCursor.moveToFirst();\n    }\n    return mCursor;\n    // [0] The change should end here (before calling the method exit)\n}", 
    "fileName": "iSENSE Mobile/src/edu/uml/cs/droidsense/comm/RestAPIDbAdapter.java", 
    "lineNumber": 405
  }

  try:
    r = requests.post("http://%s/inspect_anomaly" % address, json=service_input)
  except Exception as e:
    print(str(e))
    raise
  assert r.status_code == 200

  compare(r.json(), expected_output)

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
    "numberOfExamples" : 35.0
  }

  try:
    r = requests.post("http://%s/explain_anomaly" % address, json=service_input)
  except Exception as e:
    print(str(e))
    raise
  assert r.status_code == 200

  compare(r.json(), expected_output)

  return 0

def main(input_args=None):
  p = optparse.OptionParser()
  p.add_option('-a', '--address', help="Ip address of the solr server")
  p.add_option('-p', '--port', help="Port of the solr server")

  opts, args = p.parse_args()

  if (not opts.address):
      print("Server address not provided! (try localhost)")
      sys.exit(1)

  if (not opts.port):
      print("Server port not provided! (try 30072)")
      sys.exit(1)

  address="%s:%s" % (opts.address, opts.port)

  test_process_graph_in_pull_request(address)
  test_inspect_anomaly(address)
  test_explain_anomaly(address)
  print("All is ok!")


if __name__ == '__main__':
    main()
