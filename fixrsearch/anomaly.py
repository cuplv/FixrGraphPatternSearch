"""
Define the anomaly
"""

import string


anomaly_format = """
--------------------------------------------------------------------------------
Anomaly id: ${ID}
Repo: ${USER_NAME}/${REPO_NAME}/${COMMIT_ID}
Method: ${METHODNAME} in ${METHODFILE} at line ${METHODLINE}
Patch:
--------------------------------------------------------------------------------
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
               patch_text,
               pattern_text,
               pattern):
    # progressive id of the anomaly in the pull request
    self.numeric_id = numeric_id
    # method for which we found the anomaly
    self.method_ref = method_ref
    # ref to the pull request that generated the anomaly
    self.pull_request = pull_request
    # patch to apply to fix the anomaly
    self.patch_text = patch_text
    # pattern violated shown in the program vars
    self.pattern_text = pattern_text
    # pattern that was violated in the anomaly
    self.pattern = pattern
    # status of the anomaly
    self.status = Anomaly.Status.NEW



  def __repr__(self):
    subs = {
      "ID" : self.numeric_id,
      "REPO_NAME" : self.pull_request.repo_ref.repo_name,
      "USER_NAME" : self.pull_request.repo_ref.user_name,
      "COMMIT_ID" : self.pull_request.commit_ref.commit_hash,
      "METHODNAME" : self.method_ref.method_name,
      "METHODLINE" : str(self.method_ref.start_line_number),
      "METHODFILE" : self.method_ref.source_class_name,
      "PATCH" : self.patch_text,
      "PATTERN_TEXT" : self.pattern_text,
    }


    temp = string.Template(anomaly_format) 
    res = temp.substitute(subs)
    return res
