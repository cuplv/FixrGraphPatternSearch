"""
Define utility classes
"""


class RepoReference(object):
  """
  Reference a repository
  """
  def __init__(self, repo_name, user_name):
    self.repo_name = repo_name
    self.user_name = user_name

class CommitReference(object):
  """
  Reference a commit
  """
  def __init__(self,repo_reference, commit_hash):
    self.repo_reference = repo_reference
    self.commit_hash = commit_hash

class PullRequestReference(object):
  """
  Reference to a pull request
  """
  def __init__(self, repo_reference, number):
    self.repo_reference = repo_reference
    # number of the pull request
    self.number = number

class MethodReference(object):
  """
  Contains the sufficient data to reference a method in the corpus
  """
  def __init__(self, commit_reference,
               class_name,
               package_name,
               method_name,
               start_line_number,
               source_class_name):

    self.commit_reference = commit_reference
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

  class Type:
    ANOMALOUS = "ANOMALOUS"
    POPULAR = "POPULAR"
    ISOLATED = "ISOLATED"

  def __init__(self,
               cluster_id,
               cluster_type,
               frequency):
    # TODO: add popularity
    self.cluster_id = cluster_id
    self.cluster_type = cluster_type
    self.frequency = frequency

class PatternRef(object):
  """ Representation of the pattern
  """
  def __init__(self, cluster_ref, pattern_id, text):
    # TODO: add list of examples, add containing cluster 
    self.cluster_ref = cluster_ref
    self.pattern_id = pattern_id
    self.text = text
