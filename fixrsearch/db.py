"""
Database routines for the search tool.

"""

from fixrsearch.anomaly import Anomaly

from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.exc import OperationalError
from sqlalchemy import MetaData, Table
from sqlalchemy import ForeignKey
from sqlalchemy import Column, Integer, String, VARCHAR

from sqlalchemy.ext.declarative import declarative_base


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
        # sqlite://<nohostname>/<path>
        # where <path> is relative:
        engine = create_engine(self.get_db_name())
        return engine

class Db(object):
    def __init__(self, config):
        self.config = config
        self.engine = None
        self.connection = None

    def connect(self):
        self.engine = self.config.create_engine()
        self.connection = self.engine.connect()

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

    def create_anomaly(self,
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
        metadata = MetaData()
        
        reposTable = Table('repos', metadata,
                           Column('id', Integer, primary_key = True),
                           Column('repo_name', String(100), nullable = False),
                           Column('user_name', String(40), nullable = False))

        commitsTable = Table('commits', metadata,
                             Column('id', Integer, primary_key = True),
                             Column('repo_id', Integer, ForeignKey('repos.id')),
                             # Git SHA is 40 characters
                             Column('commit_hash', String(40), nullable = False))
                            
        pullRequestTable = Table('pull_requests', metadata,
                                 Column('id', Integer, primary_key = True),
                                 Column('repo_id', Integer, ForeignKey('repos.id')),
                                 Column('number', Integer, nullable = False))

        methodsTable = Table('methods', metadata,
                             Column('id', Integer, primary_key = True),
                             Column('commit_id', Integer, ForeignKey('commits.id')),
                             Column('class_name', VARCHAR, nullable = False),
                             Column('package_name', VARCHAR, nullable = False),
                             Column('method_name', VARCHAR, nullable = False),
                             Column('start_line_number', Integer, nullable = False),
                             Column('source_class_name', VARCHAR, nullable = False))
                             
        patternsTable = Table('patterns', metadata,
                             Column('id', Integer, primary_key = True),
                             Column('repo_id', Integer, ForeignKey('repos.id')))

        patchesTable = Table('patches', metadata,
                             Column('id', Integer, primary_key = True),
                             Column('patch', VARCHAR, ForeignKey('repos.id')))

        anomaliesTable = Table('anomalies', metadata,
                               Column('id', Integer, primary_key=True),
                               Column('method_id', Integer, ForeignKey('methods.id')),
                               Column('pull_request_id', Integer,
                                      ForeignKey('pull_requests.id')),
                               Column('pattern_id', Integer, ForeignKey('patterns.id')),
                               Column('patch_id', Integer, ForeignKey('patches.id')),
                               Column('status', Integer, ForeignKey('patches.id'))
        )
        
        metadata.create_all(self.engine)
        
