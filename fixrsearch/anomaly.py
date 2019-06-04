"""
Define the anomaly
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


