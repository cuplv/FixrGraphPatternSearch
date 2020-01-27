"""
Define the anomaly
"""

import string
import json

from fixrsearch.utils import (
  RepoRef,
  PullRequestRef,
  CommitRef,
  MethodRef,
  ClusterRef,
  PatternRef
)


anomaly_format = """
--------------------------------------------------------------------------------
Anomaly id: ${ID}
Repo: ${USER_NAME}/${REPO_NAME}/${COMMIT_ID}
Method: ${METHODNAME} in ${METHODFILE} at line ${METHODLINE}
--------------------------------------------------------------------------------
Description:
${DESCRIPTION}
Patch:
${PATCH}
--------------------------------------------------------------------------------
Pattern:
--------------------------------------------------------------------------------
${PATTERN_TEXT}
--------------------------------------------------------------------------------

"""

class Anomaly(object):
  class Status:
    NEW = "new"
    SOLVED = "solved"

  def __init__(self,
               numeric_id,
               method_ref,
               pull_request,
               description,
               patch_text,
               pattern_text,
               pattern,
               git_path):
    # progressive id of the anomaly in the pull request
    self.numeric_id = numeric_id
    # method for which we found the anomaly
    self.method_ref = method_ref
    # ref to the pull request that generated the anomaly
    self.pull_request = pull_request
    # textual description of the anomaly 
    self.description = description
    # patch to apply to fix the anomaly
    self.patch_text = patch_text
    # pattern violated shown in the program vars
    self.pattern_text = pattern_text
    # pattern that was violated in the anomaly
    self.pattern = pattern
    # path to the file in the git repo
    self.git_path= git_path
    # status of the anomaly
    self.status = Anomaly.Status.NEW



  def __repr__(self):
    repo_name = ""
    user_name = ""
    commit_hash = ""
    if not self.pull_request is None:
      if not self.pull_request.repo_ref is None:
        repo_name = self.pull_request.repo_ref.repo_name
        user_name = self.pull_request.repo_ref.user_name

      if not self.pull_request.commit_ref is None:
        commit_hash = self.pull_request.commit_ref.commit_hash

    method_name = ""
    start_line_number = ""
    source_class_name = ""
    if not self.method_ref is None:
      method_name = self.method_ref.method_name
      start_line_number = str(self.method_ref.start_line_number)
      source_class_name = self.method_ref.source_class_name

    subs = {
      "ID" : self.numeric_id,
      "REPO_NAME" : repo_name,
      "USER_NAME" : user_name,
      "COMMIT_ID" : commit_hash,
      "METHODNAME" : method_name,
      "METHODLINE" : start_line_number,
      "METHODFILE" : source_class_name,
      "GIT_PATH" : self.git_path,
      "DESCRIPTION" : self.description,
      "PATCH" : self.patch_text,
      "PATTERN_TEXT" : self.pattern_text,
    }

    temp = string.Template(anomaly_format) 
    res = temp.substitute(subs)
    return res


class AnomalyEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, RepoRef):
      return {"repo_name" : obj.repo_name, "user_name" : obj.user_name}
    elif isinstance(obj, CommitRef):
      return {
        "repo_ref" : self.default(obj.repo_ref),
        "commit_hash" : obj.commit_hash,
      }
    elif isinstance(obj,PullRequestRef):
      return {
        "repo_ref" : self.default(obj.repo_ref),
        "number" : obj.number,
        "commit_ref" : self.default(obj.commit_ref),
      }
    elif isinstance(obj, MethodRef):
      return {
        "commit_ref" : self.default(obj.commit_ref),
        "class_name" : obj.class_name,
        "package_name" : obj.package_name,
        "method_name" : obj.method_name,
        "start_line_number" : obj.start_line_number,
        "source_class_name" : obj.source_class_name,
      }
    elif isinstance(obj, ClusterRef):
      return {
        "cluster_id" : obj.cluster_id,
        "methods" : obj.methods,
      }
    elif isinstance(obj, PatternRef):
      return {
        "cluster_ref" : self.default(obj.cluster_ref),
        "pattern_id" : obj.pattern_id,
        "pattern_type" : obj.pattern_type,
        "frequency" : obj.frequency,
        "cardinality" : obj.cardinality,
      }
    elif isinstance(obj, Anomaly):
      return {
        "numeric_id" : obj.numeric_id,
        "method_ref" : self.default(obj.method_ref),
        "pull_request" : obj.pull_request,
        "description" : obj.description,
        "patch_text" : obj.patch_text,
        "pattern_text" : obj.pattern_text,
        "pattern" : self.default(obj.pattern),
        "git_path:" : obj.git_path,
        "status" : obj.status,
      }
    else:
      return json.JSONEncoder.default(self, obj)
