"""
Define the anomaly and the operation 

"""

from fixrsearch.utils import (
  MethodReference
)

class Anomaly(object):
  class Status:
    NEW = "new"
    SOLVED = "solved"

  def __init__(self,
               numeric_id,
               method_reference,
               pull_request,
               patch,
               pattern):
    # progressive id of the anomaly in the pull request
    self.numeric_id = numeric_id
    # method for which we found the anomaly
    self.method_reference = method_reference
    # reference to the pull request that generated the anomaly
    self.pull_request = pull_request
    # pattern that was violated in the anomaly
    self.pattern = pattern
    # patch to apply to fix the anomaly
    self.patch = patch
    # status of the anomaly
    self.status = Anomaly.Status.NEW

