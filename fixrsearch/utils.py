"""
Define utility classes
"""


class RepoReference(object):
  """
  Reference a repository
  """
  def __init__(self):
    self.repo_name = None
    self.user_name = None

class CommitReference(object):
  """
  Reference a commit
  """
  def __init__(self):
    self.repo_name = None
    self.commit_hash = None

class PullRequestReference(object):
  """
  Reference to a pull request
  """
  def __init__(self):
    self.repo_reference = None
    # number of the pull request
    self.number = None

class MethodReference(object):
  """
  Contains the sufficient data to reference a method in the corpus
  """
  def __init__(self):
    self.commit_reference = None
    # Name of the class including the package
    self.class_name = None
    # Package of the class
    self.package_name = None
    # simple name of the method
    self.method_name = None    
    # line number of the method
    self.method_line_number = None
    # Name of the source code file of the method
    self.source_class_name = None

class Pattern(object):
  """
  """
  def __init__(self):
    # TODO: complete the Pattern object
    self.repo_reference = None
    self.text = None
