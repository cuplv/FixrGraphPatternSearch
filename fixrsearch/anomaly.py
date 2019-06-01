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
    self.method_reference = method_reference
    self.pull_request = pull_request
    self.pattern = pattern
    self.patch = patch
    self.status = Anomaly.Status.NEW

