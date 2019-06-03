"""
Database routines for the search tool.

"""

import functools
from fixrsearch.anomaly import Anomaly

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.exc import OperationalError
from sqlalchemy import MetaData, Table
from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, String, Float, VARCHAR

from sqlalchemy.sql import select
from sqlalchemy.ext.declarative import declarative_base

from fixrsearch.utils import (
  RepoReference, CommitReference,
  PullRequestReference,
  MethodReference,
  ClusterRef,
  PatternRef)

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

    def new_repo(self, repo_ref, lookup=False):
      return self._new_data(repo_ref, self._new_repo, self.get_repo, lookup)

    def get_repo(self, repo_ref):
      return self._get_data(repo_ref, self._select_repo)

    def get_repo_by_id(self, repo_id):
      repos = self.metadata.tables['repos']
      stmt = select([repos]).where (repos.c.id == repo_id).limit(1)
      res = self.connection.execute(stmt)
      res_data = res.fetchone()
      if (res_data is None):
        return None
      else:
        return RepoReference(res_data.repo_name,
                             res_data.user_name)

    def new_commit(self, commit_ref, lookup=False):
      return self._new_data(commit_ref, self._new_commit,
                            self.get_commit, lookup)
    def get_commit(self, commit_ref):
      return self._get_data(commit_ref, self._select_commit)

    def get_commit_by_id(self, commit_id):
      commits = self.metadata.tables['commits']
      stmt = select([commits]).where (commits.c.id == commit_id).limit(1)
      res = self.connection.execute(stmt)
      res_data = res.fetchone()
      if (res_data is None):
        return None
      else:
        repo_ref = self.get_repo_by_id(res_data.repo_id)
        assert not repo_ref is None

        return CommitReference(repo_ref,
                               res_data.commit_hash)

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

    def get_pattern_by_id(self, pattern_db_id):
      patterns = self.metadata.tables['patterns']
      stmt = select([patterns]).where (patterns.c.id == pattern_db_id).limit(1)
      res = self.connection.execute(stmt)
      res_data = res.fetchone()
      if (res_data is None):
        return None
      else:
        cluster_ref = self.get_cluster_by_id(res_data.cluster_id)
        return PatternRef(cluster_ref,
                          res_data.pattern_id,
                          res_data.text)

    def new_cluster(self, cluster_ref, lookup=False):
      return self._new_data(cluster_ref, self._new_cluster,
                            self.get_cluster, lookup)
    def get_cluster(self, cluster_ref):
      return self._get_data(cluster_ref, self._select_cluster)

    def get_cluster_by_id(self, cluster_db_id):
      clusters = self.metadata.tables['clusters']
      stmt = select([clusters]).where (clusters.c.id == cluster_db_id).limit(1)
      res = self.connection.execute(stmt)
      res_data = res.fetchone()
      if (res_data is None):
        return None
      else:
        return ClusterRef(res_data.cluster_id,
                          res_data.cluster_type,
                          res_data.frequency)


    def new_method(self, data, lookup=False):
      return self._new_data(data, self._new_method,
                            self.get_method, lookup)
    def get_method(self, data):
      return self._get_data(data, self._select_method)

    def get_method_by_id(self, method_id):
      methods = self.metadata.tables['methods']
      stmt = select([methods]).where (methods.c.id == method_id).limit(1)
      res = self.connection.execute(stmt)
      res_data = res.fetchone()

      if (res_data is None):
        return None
      else:
        commit_ref = self.get_commit_by_id(res_data.commit_id)

        return MethodReference(commit_ref,
                               res_data.class_name,
                               res_data.package_name,
                               res_data.method_name,
                               res_data.start_line_number,
                               res_data.source_class_name)


    def new_anomaly(self, data, lookup=False):
      return self._new_data(data, self._new_anomaly,
                            self.get_anomaly, lookup)
    def get_anomaly(self, data):
      return self._get_data(data, self._select_anomaly)

    def get_anomaly_by_pr_and_number(self,
                                     pull_request,
                                     numeric_id):
      """ Return the anomaly for the given pull requesta witgh the given
      numeric_id of the anomaly
      """
      anomalies = self.metadata.tables['anomalies']

      select_pr = self._select_pr(pull_request).alias()
      select_anomaly = select([anomalies]). \
        where (anomalies.c.pull_request_id == select_pr.c.id and
               anomalies.c.numeric_id == numeric_id).limit(1)

      exec_res = self.connection.execute(select_anomaly)
      res = exec_res.fetchone()

      if (res is None):
        return None
      else:
        pattern = self.get_pattern_by_id(res.pattern_id)
        assert (pattern is not None)
        method = self.get_method_by_id(res.method_id)
        assert (method is not None)

        anomaly = Anomaly(numeric_id,
                          method,
                          pull_request,
                          res.patch,
                          pattern)
        return anomaly

    def get_anomalies(self, pull_request):
        """ Return the list of anomalies found in the
        pull_request
        """
        raise NotImplementedError


    def _new_data(self, data, new_f, get_f, lookup=False):
      if (lookup):
        res_get_f = get_f(data)

        if (res_get_f is None):
          (data_id, data) = new_f(data)
        else:
          (data_id, data) = res_get_f

        return (data_id, data)
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
      stmt = self._select_repo(commit_reference.repo_reference).alias()
      return select([commits]). \
        where (commits.c.commit_hash == commit_reference.commit_hash and 
               commits.c.repo_id == stmt.c.id).limit(1)

    def _new_pr(self, pr_ref):
      (repo_id, _) = self.new_repo(pr_ref.repo_reference, True)
      pull_requests = self.metadata.tables['pull_requests']

      ins = pull_requests.insert().values(repo_id = repo_id,
                                          number = pr_ref.number)
      result = self.connection.execute(ins)
      return (result.inserted_primary_key[0], pr_ref)

    def _select_pr(self, pr_ref):
      prs = self.metadata.tables['pull_requests']
      stmt1 = self._select_repo(pr_ref.repo_reference).alias()
      return select([prs]). \
        where (prs.c.number == pr_ref.number and
               prs.c.repo_id == stmt1.c.id).limit(1)

    def _new_pattern(self, pattern_ref):
      patterns = self.metadata.tables['patterns']
      (cluster_id, _) = self.new_cluster(pattern_ref.cluster_ref, True)
      ins = patterns.insert().values(cluster_id=cluster_id,
                                     pattern_id=pattern_ref.pattern_id,
                                     text=pattern_ref.text)
      result = self.connection.execute(ins)
      return (result.inserted_primary_key[0], pattern_ref)

    def _select_pattern(self, pattern_ref):
      patterns = self.metadata.tables['patterns']
      stmt_cluster = self._select_cluster(pattern_ref.cluster_ref).alias()

      return select([patterns]). \
        where (patterns.c.cluster_id == stmt_cluster.c.id and 
               patterns.c.pattern_id == pattern_ref.pattern_id).limit(1)

    def _new_cluster(self, cluster_ref, lookup=False):
      clusters = self.metadata.tables['clusters']
      ins = clusters.insert().values(cluster_id=cluster_ref.cluster_id,
                                     cluster_type=cluster_ref.cluster_type,
                                     frequency=cluster_ref.frequency)
      result = self.connection.execute(ins)
      return (result.inserted_primary_key[0], cluster_ref)

    def _select_cluster(self, cluster_ref):
      clusters = self.metadata.tables['clusters']
      return select([clusters]). \
        where (clusters.c.cluster_id == cluster_ref.cluster_id).limit(1)

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
      # rename stuff to avoid ambiguities
      stmt1 = stmt1.alias()

      return select([methods]). \
        where (methods.c.commit_id == stmt1.c.id and
               methods.c.class_name == data.class_name and
               methods.c.package_name == data.package_name and
               methods.c.method_name == data.method_name and
               methods.c.start_line_number == data.start_line_number and
               methods.c.source_class_name == data.source_class_name).limit(1)

    def _new_anomaly(self, anomaly):
      anomalies = self.metadata.tables['anomalies']

      (method_id, _) = self.new_method(anomaly.method_reference, True)
      (pull_request_id, _) = self.new_pr(anomaly.pull_request, True)
      (pattern_id, _) = self.new_pattern(anomaly.pattern, True)

      ins = anomalies.insert().values(method_id = method_id,
                                      pull_request_id = pull_request_id,
                                      pattern_id = pattern_id,
                                      numeric_id = anomaly.numeric_id,
                                      patch = anomaly.patch,
                                      status = anomaly.status)

      result = self.connection.execute(ins)
      return (result.inserted_primary_key[0], anomaly)

    def _select_anomaly(self, data):
      anomalies = self.metadata.tables['anomalies']

      stmt_method = self._select_method(data.method_reference)
      stmt_pr = self._select_pr(data.pull_request)
      stmt_pattern = self._select_pattern(data.pattern)

      return select([anomalies]). \
        where (anomalies.c.method_id == stmt_method.c.id and
               anomalies.c.pull_request_id == stmt_pr.c.id and
               anomalies.c.pattern_id == stmt_pattern.c.id and
               anomalies.c.numeric_id == data.anomaly.numeric_id and
               anomalies.c.patch == data.anomaly.patch and
               anomalies.c.status == data.anomaly.status).limit(1)

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

        clustersTable = Table('clusters', self.metadata,
                              Column('id', Integer, primary_key = True),
                              Column('cluster_id', String(255)),
                              Column('cluster_type', String(15)),
                              Column('frequency', Float))

        patternsTable = Table('patterns', self.metadata,
                              Column('id', Integer, primary_key = True),
                              Column('cluster_id', Integer, ForeignKey('clusters.id')),
                              Column('pattern_id', String(255)),
                              Column('text', VARCHAR))

        anomaliesTable = Table('anomalies', self.metadata,
                               Column('id', Integer, primary_key=True),
                               Column('numeric_id', Integer),
                               Column('method_id', Integer, ForeignKey('methods.id')),
                               Column('pull_request_id', Integer,
                                      ForeignKey('pull_requests.id')),
                               Column('pattern_id', Integer, ForeignKey('patterns.id')),
                               Column('patch', VARCHAR),
                               Column('status', VARCHAR))

        self.metadata.create_all(self.engine)

