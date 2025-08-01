from .general import Base, orm_get, db_session
from datetime import datetime
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy import Table, Column, String, Integer, ForeignKey, Boolean, DateTime, Float, JSON
from sqlalchemy.orm import backref, relationship
from six import with_metaclass
import epmt.epmt_settings as settings

if 'postgres' in settings.db_params.get('url', ''):
    from sqlalchemy.dialects.postgresql import JSONB as JSON


####### IMPORTANT #########
# Please do NOT edit any of the models in this file directly.
# Instead read docs/migration.md and create a migration script.
# Then run "alembic upgrade head"
###########################

# Control what gets exported when using "from .models import *"
__all__ = [
    'CommonMeta', 'User', 'Host', 'ReferenceModel', 'Job', 'UnprocessedJob', 'Process',
    'refmodel_job_associations_table', 'host_job_associations_table', 'ancestor_descendant_associations_table'
]


class CommonMeta(DeclarativeMeta):
    def __getitem__(cls, index):
        obj = orm_get(cls, index)
        if obj is None:
            raise KeyError('{0}[{1}] could not be found'.format(cls.__name__, index))
        else:
            return obj


refmodel_job_associations_table = Table('refmodel_job_associations', Base.metadata,
                                        Column('jobid', String, ForeignKey('jobs.jobid'), primary_key=True),
                                        Column('refmodel_id', Integer, ForeignKey('refmodels.id'), primary_key=True)
                                        )

host_job_associations_table = Table('host_job_associations', Base.metadata,
                                    Column(
                                        'jobid', String, ForeignKey(
                                            'jobs.jobid', ondelete="CASCADE"), primary_key=True),
                                    Column('hostname', String, ForeignKey('hosts.name'), primary_key=True)
                                    )

ancestor_descendant_associations_table = Table('ancestor_descendant_associations', Base.metadata,
                                               Column(
                                                   'ancestor', Integer, ForeignKey(
                                                       'processes.id', ondelete="CASCADE"), primary_key=True),
                                               Column(
                                                   'descendant', Integer, ForeignKey(
                                                       'processes.id', ondelete="CASCADE"), primary_key=True)
                                               )


class User(with_metaclass(CommonMeta, Base)):
    __tablename__ = 'users'
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    name = Column(String, primary_key=True)
    id = Column(Integer, unique=True)
    info_dict = Column(JSON)
    jobs = relationship('Job', back_populates='user')
    processes = relationship('Process', back_populates='user')

    @db_session
    def __repr__(self):
        return "User['%s']" % (self.name)


class Host(with_metaclass(CommonMeta, Base)):
    __tablename__ = 'hosts'
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    name = Column(String, primary_key=True)
    info_dict = Column(JSON)
    processes = relationship('Process', back_populates='host')
    jobs = relationship('Job', back_populates='hosts', secondary=host_job_associations_table)

    @db_session
    def __repr__(self):
        return "Host['%s']" % (self.name)


class ReferenceModel(with_metaclass(CommonMeta, Base)):
    __tablename__ = 'refmodels'
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    id = Column(Integer, primary_key=True)
    tags = Column(JSON, index=True)
    op_tags = Column(JSON, index=True)
    computed = Column(JSON)
    enabled = Column(Boolean, default=True)
    info_dict = Column(JSON)
    jobs = relationship('Job', back_populates='ref_models', secondary=refmodel_job_associations_table)
    name = Column(String, index=True, unique=True)

    @db_session
    def __repr__(self):
        return "ReferenceModel[%d]" % (self.id)


class Job(with_metaclass(CommonMeta, Base)):
    __tablename__ = 'jobs'
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, onupdate=datetime.now)
    info_dict = Column(JSON, default={})
    annotations = Column(JSON, default={}, index=True)
    analyses = Column(JSON, default={}, index=True)
    start = Column(DateTime, default=datetime.now, index=True)
    end = Column(DateTime, default=datetime.now)
    duration = Column(Float, default=0)
    proc_sums = Column(JSON)  # aggregates across processes of job
    env_dict = Column(JSON)
    env_changes_dict = Column(JSON)
    submit = Column(DateTime)
    jobid = Column(String, primary_key=True, index=True)
    jobname = Column(String)
    exitcode = Column(Integer)

    user_id = Column(String, ForeignKey('users.name'))
    user = relationship('User', back_populates="jobs")

    processes = relationship('Process', cascade="all", back_populates="job")
    hosts = relationship('Host', back_populates='jobs', secondary=host_job_associations_table)
    tags = Column(JSON, index=True)
    # exclusive cpu time
    cpu_time = Column(Float)
    ref_models = relationship('ReferenceModel', back_populates="jobs", secondary=refmodel_job_associations_table)

    @db_session
    def __repr__(self):
        return "Job['%s']" % (self.jobid)


class UnprocessedJob(with_metaclass(CommonMeta, Base)):
    __tablename__ = 'unprocessed_jobs'
    created_at = Column(DateTime, default=datetime.now)
    info_dict = Column(JSON, default={})
    jobid = Column(String, ForeignKey('jobs.jobid', ondelete="CASCADE"), primary_key=True)
    job = relationship('Job')

    def __repr__(self):
        return "UnprocessedJob['%s']" % (self.jobid)


class Process(with_metaclass(CommonMeta, Base)):
    __tablename__ = 'processes'
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    info_dict = Column(JSON)
    id = Column(Integer, primary_key=True)

    user_id = Column(String, ForeignKey('users.name'))
    user = relationship('User', back_populates="processes")

    jobid = Column(String, ForeignKey('jobs.jobid', ondelete="CASCADE"), index=True)
    job = relationship('Job', back_populates='processes')

    start = Column(DateTime, default=datetime.now, index=True)
    end = Column(DateTime, default=datetime.now)
    duration = Column(Float, default=0)
    tags = Column(JSON, index=True)

    host_id = Column(String, ForeignKey('hosts.name'))
    host = relationship('Host', back_populates="processes")

    threads_df = Column(JSON)
    threads_sums = Column(JSON)
    numtids = Column(Integer, default=1)
    # exclusive cpu time
    cpu_time = Column(Float)
    # sum of cpu times of all descendants + process_cpu_time
    inclusive_cpu_time = Column(Float)
    exename = Column(String)
    path = Column(String)
    args = Column(String)
    pid = Column(Integer)
    ppid = Column(Integer)
    pgid = Column(Integer)
    sid = Column(Integer)
    gen = Column(Integer)
    exitcode = Column(Integer)
    # for creating a process graph
    # a child process is also included in the list of descendants
    # while parent is included in the ancestors
    parent_id = Column(Integer, ForeignKey('processes.id'), index=True)
    children = relationship('Process', backref=backref('parent', remote_side=[id]))
    # ancestors = relationship('ProcessAssociation',backref='descendants', primaryjoin=id==ProcessAssociation.fk_ancestor)
    # descendants = relationship('ProcessAssociation',backref='ancestors', primaryjoin=id==ProcessAssociation.fk_descendant )
    ancestors = relationship(
        'Process',
        backref='descendants',
        secondary=ancestor_descendant_associations_table,
        primaryjoin=id == ancestor_descendant_associations_table.c.descendant,
        secondaryjoin=id == ancestor_descendant_associations_table.c.ancestor)
    depth = Column(Integer)   # depth in process tree, root process has depth 0

    @db_session
    def __repr__(self):
        return "Process[%d]" % (self.id)

# from sqlalchemy import event
# @event.listens_for(Table, "column_reflect")
# def column_reflect(inspector, table, column_info):
#     # set column.key = "attr_<lower_case_name>"
#     column_info['key'] = column_info['name']
