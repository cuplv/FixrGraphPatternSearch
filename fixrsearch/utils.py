"""
Define utility classes
"""


class RepoRef(object):
  """
  Reference a repository
  """
  def __init__(self, repo_name, user_name):
    self.repo_name = repo_name
    self.user_name = user_name

class CommitRef(object):
  """
  Reference a commit
  """
  def __init__(self,repo_ref, commit_hash):
    self.repo_ref = repo_ref
    self.commit_hash = commit_hash

class PullRequestRef(object):
  """
  Reference to a pull request
  """
  def __init__(self, repo_ref, number, commit_ref):
    self.repo_ref = repo_ref
    # number of the pull request
    self.number = number
    self.commit_ref = commit_ref

class MethodRef(object):
  """
  Contains the sufficient data to reference a method in the corpus
  """
  def __init__(self,
               commit_ref,
               class_name,
               package_name,
               method_name,
               start_line_number,
               source_class_name):

    self.commit_ref = commit_ref
    # Name of the class including the package
    self.class_name = class_name
    # Package of the class
    self.package_name = package_name
    # simple name of the method
    self.method_name = method_name
    # line number of the method
    self.start_line_number = start_line_number
    # Name of the source code file of the method
    self.source_class_name = source_class_name


class ClusterRef(object):
  """ Represent a cluster
  """

  SEPARATOR = ","

  def __init__(self, cluster_id, methods):
    self.cluster_id = cluster_id
    # List of methods, comma separated
    self.methods = methods

  def get_method_list(self):
    l = [m in self.methods.split[ClusterRef.SEPARATOR]]
    return l

  @staticmethod
  def build_methods_str(method_list):
    return ClusterRef.SEPARATOR.join(method_list)


class PatternRef(object):
  """ Representation of the pattern
  """
  class Type:
    ANOMALOUS = "ANOMALOUS"
    POPULAR = "POPULAR"
    ISOLATED = "ISOLATED"

  def __init__(self, cluster_ref, pattern_id, pattern_type):
    # TODO: add list of examples
    self.cluster_ref = cluster_ref
    self.pattern_id = pattern_id
    self.pattern_type = pattern_type
