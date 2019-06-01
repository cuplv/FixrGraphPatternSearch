"""
Database routines for the search tool.

"""

import functools
from fixrsearch.anomaly import Anomaly

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.exc import OperationalError
from sqlalchemy import MetaData, Table
from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, String, VARCHAR

from sqlalchemy.sql import select
from sqlalchemy.ext.declarative import declarative_base

from fixrsearch.utils import (
  RepoReference, CommitReference,
  PullRequestReference,
  MethodReference,
  Pattern)

class DbConfig(object):
    def create_engine(self):
        raise NotImplementedError

    def get_db_name(self):
        raise NotImplementedError

class SQLiteConfig(DbConfig):
    def __init__(self, filename):
        self.filename = filename

    def get_db_name(self):
        db_name = "sqlite:///%s" % self.filename
        return db_name

    def create_engine(self):
        engine = create_engine(self.get_db_name())
        return engine

class Db(object):
    def __init__(self, config):
        self.config = config
        self.engine = None
        self.connection = None
        self.metadata = None

    def connect(self):
        self.engine = self.config.create_engine()
        self.connection = self.engine.connect()
        self.metadata = Metadata()
        self.metadata.reflect(bind=self.engine)

    def connect_or_create(self):
        self.engine = self.config.create_engine()

        try:
            self.engine.connect()
            self.engine.execute("SHOW DATABASES")
        except OperationalError:
            self.engine = self.config.create_engine()
            self._create_db()

        self.connection = self.engine.connect()

    def disconnect(self):
        assert not self.connection is None
        self.connection.close()
        self.connection = None

    def get_pattern(self,
                    pull_request,
                    anomaly_numeric_id):
        raise NotImplementedError

    def get_anomaly(self, pull_request, anomaly_numeric_id):
        """ Return the specific anomaly
        """
        raise NotImplementedError

    def get_anomalies(self, pull_request):
        """ Return the list of anomalies found in the
        pull_request
        """
        raise NotImplementedError

    def new_repo(self, repo_ref, lookup=False):
      return self._new_data(repo_ref, self._new_repo, self.get_repo, lookup)

    def get_repo(self, repo_ref):
      return self._get_data(repo_ref, self._select_repo)

    def new_commit(self, commit_ref, lookup=False):
      return self._new_data(commit_ref, self._new_commit,
                            self.get_commit, lookup)
    def get_commit(self, commit_ref):
      return self._get_data(commit_ref, self._select_commit)

    def new_pr(self, pr_ref, lookup=False):
      return self._new_data(pr_ref, self._new_pr,
                            self.get_pr, lookup)
    def get_pr(self, pr_ref):
      return self._get_data(pr_ref, self._select_pr)

    def new_pattern(self, pattern_ref, lookup=False):
      return self._new_data(pattern_ref, self._new_pattern,
                            self.get_pattern, lookup)
    def get_pattern(self, pattern_ref):
      return self._get_data(pattern_ref, self._select_pattern)

    def new_method(self, data, lookup=False):
      return self._new_data(data, self._new_method,
                            self.get_method, lookup)
    def get_method(self, data):
      return self._get_data(data, self._select_method)


    def _new_data(self, data, new_f, get_f, lookup=False):
      if (lookup):
        data_id = get_f(data)

        if (data_id is None):
          (data_id, new_repo) = new_f(data)

        return (data_id, new_repo)
      else:
        return new_f(data)

    def _get_data(self, data, select_f):
      stmt = select_f(data)
      result = self.connection.execute(stmt)
      res = result.fetchone()

      if (res is None):
        return None
      else:
        return (res.id, data)


    def _new_repo(self, repo_ref):
      repos = self.metadata.tables['repos']
      ins = repos.insert().values(repo_name=repo_ref.repo_name,
                                  user_name=repo_ref.user_name)
      result = self.connection.execute(ins)
      return (result.inserted_primary_key[0], repo_ref)

    def _select_repo(self, repo_reference):
      repos = self.metadata.tables['repos']
      return select([repos]). \
        where(repos.c.user_name == repo_reference.user_name and
              repos.c.repo_name == repo_reference.repo_name).limit(1)

    def _new_commit(self, commit_ref):
      (repo_id, _) = self.new_repo(commit_ref.repo_reference, True)
      commits = self.metadata.tables['commits']
      ins = commits.insert().values(repo_id=repo_id,
                                    commit_hash=commit_ref.commit_hash)

      result = self.connection.execute(ins)
      return (result.inserted_primary_key[0], commit_ref)

    def _select_commit(self, commit_reference):
      commits = self.metadata.tables['commits']
      stmt1 = self._select_repo(commit_reference.repo_reference)
      stmt = select([commits]). \
             where (commits.c.commit_hash == commit_reference.commit_hash and 
                    commits.c.repo_id == stmt1.id).limit(1)
      return stmt

    def _new_pr(self, pr_ref, lookup=False):
      (repo_id, _) = self.new_repo(pr_ref.repo_reference, True)
      pull_requests = self.metadata.tables['pull_requests']
      ins = pull_requests.insert().values(repo_id=repo_id,
                                          number=pr_ref.number)
      result = self.connection.execute(ins)
      return (result.inserted_primary_key[0], pr_ref)

    def _select_pr(self, pr_ref):
      prs = self.metadata.tables['pull_requests']
      stmt1 = self._select_repo(pr_ref.repo_reference)
      return select([prs]). \
        where (prs.c.number == pr_ref.number and
               prs.c.repo_id == stmt1.id).limit(1)

    def _new_pattern(self, pattern_ref, lookup=False):
      (repo_id, _) = self.new_repo(pattern_ref.repo_reference, True)
      patterns = self.metadata.tables['patterns']
      ins = patterns.insert().values(repo_id=repo_id,
                                     pattern_id=pattern_ref.pattern_id)
      result = self.connection.execute(ins)
      return (result.inserted_primary_key[0], pattern_ref)

    def _select_pattern(self, pattern_ref):
      patterns = self.metadata.tables['patterns']
      stmt1 = self._select_repo(pattern_ref.repo_reference)
      return select([patterns]). \
        where (patterns.c.pattern_id == pattern_ref.pattern_id and
               patterns.c.repo_id == stmt1.id).limit(1)

    def _new_method(self, method_data):
      methods = self.metadata.tables['methods']
      (commit_id, _) = self.new_commit(method_data.commit_reference, True)

      ins = methods.insert().values(commit_id = commit_id,
                                    class_name = method_data.class_name,
                                    package_name = method_data.package_name,
                                    method_name = method_data.method_name,
                                    start_line_number = method_data.start_line_number,
                                    source_class_name = method_data.source_class_name)
      result = self.connection.execute(ins)
      return (result.inserted_primary_key[0], method_data)

    def _select_method(self, data):
      methods = self.metadata.tables['methods']

      stmt1 = self._select_commit(data.commit_reference)
      return select([methods]). \
        where (methods.commit_id == stmt1.id and
               class_name == data.class_name,
               package_name == data.package_name,
               method_name == data.method_name,
               start_line_number == data.start_line_number,
               source_class_name == data.source_class_name).limit(1)

    # patterns, patches, anomalies

    def new_anomaly(self,
                    method_reference,
                    pull_request,
                    pattern):

        anomaly = Anomaly(-1,
                          method_reference,
                          pull_request,
                          pattern)

        # insert anomaly in the db

        # return anomaly
        raise NotImplementedError


    def _create_db(self):
        # Create the database
        self.metadata = MetaData()

        reposTable = Table('repos', self.metadata,
                           Column('id', Integer, primary_key = True),
                           Column('repo_name', String(100), nullable = False),
                           Column('user_name', String(40), nullable = False))

        commitsTable = Table('commits', self.metadata,
                             Column('id', Integer, primary_key = True),
                             Column('repo_id', Integer, ForeignKey('repos.id')),
                             # Git SHA is 40 characters
                             Column('commit_hash', String(40), nullable = False))

        pullRequestTable = Table('pull_requests', self.metadata,
                                 Column('id', Integer, primary_key = True),
                                 Column('repo_id', Integer, ForeignKey('repos.id')),
                                 Column('number', Integer, nullable = False))

        methodsTable = Table('methods', self.metadata,
                             Column('id', Integer, primary_key = True),
                             Column('commit_id', Integer, ForeignKey('commits.id')),
                             Column('class_name', VARCHAR, nullable = False),
                             Column('package_name', VARCHAR, nullable = False),
                             Column('method_name', VARCHAR, nullable = False),
                             Column('start_line_number', Integer, nullable = False),
                             Column('source_class_name', VARCHAR, nullable = False))

        patternsTable = Table('patterns', self.metadata,
                              Column('id', Integer, primary_key = True),
                              Column('pattern_id', String(255)),
                              Column('repo_id', Integer, ForeignKey('repos.id')))

        patchesTable = Table('patches', self.metadata,
                             Column('id', Integer, primary_key = True),
                             Column('patch', VARCHAR, ForeignKey('repos.id')))

        anomaliesTable = Table('anomalies', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('method_id', Integer, ForeignKey('methods.id')),
                               Column('pull_request_id', Integer,
                                      ForeignKey('pull_requests.id')),
                               Column('pattern_id', Integer, ForeignKey('patterns.id')),
                               Column('patch_id', Integer, ForeignKey('patches.id')),
                               Column('status', Integer, ForeignKey('patches.id'))
        )

        self.metadata.create_all(self.engine)

