import general as db
import datetime


refmodel_job_associations_table = db.Table('refmodel_job_associations', db.Base.metadata,
    db.Column('jobid', db.String, db.ForeignKey('jobs.jobid')),
    db.Column('refmodel_id', db.Integer, db.ForeignKey('refmodels.id'))
)


class User(db.Base):
    __tablename__ = 'users'
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=datetime.datetime.now)
    name = db.Column(db.String, unique=True)
    id = db.Column(db.Integer, primary_key = True)
    jobs = db.relationship('Job', back_populates='user')

class Host(db.Base):
    __tablename__ = 'hosts'
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=datetime.datetime.now)
    name = db.Column(db.String, primary_key=True)
    processes = db.relationship('Process', back_populates='host')

class ReferenceModel(db.Base):
    __tablename__ = 'refmodels'
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=datetime.datetime.now)
    id = db.Column(db.Integer, primary_key = True)
    tags = db.Column(db.JSON)
    op_tags = db.Column(db.JSON)
    computed = db.Column(db.JSON)
    jobs = db.relationship('Job', back_populates='ref_models', secondary=refmodel_job_associations_table)

class Job(db.Base):
    __tablename__ = 'jobs'
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=datetime.datetime.now)

    start = db.Column(db.DateTime, default=datetime.datetime.now)
    end = db.Column(db.DateTime, default=datetime.datetime.now)
    duration = db.Column(db.Float, default=0)
    proc_sums = db.Column(db.JSON) # aggregates across processes of job
    env_dict = db.Column(db.JSON)
    env_changes_dict = db.Column(db.JSON)
    submit = db.Column(db.DateTime)
    jobid = db.Column(db.String, primary_key=True)
    jobname = db.Column(db.String)
    exitcode = db.Column(db.Integer)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates = "jobs")

    processes = db.relationship('Process', cascade="all,delete", backref="job")
    tags = db.Column(db.JSON)
    # exclusive cpu time
    cpu_time = db.Column(db.Float)
    ref_models = db.relationship('ReferenceModel', back_populates="jobs", secondary=refmodel_job_associations_table)

class ProcessAssociation(db.Base):
    __tablename__ = 'process_associations'
    fk_ancestor = db.Column(db.Integer, db.ForeignKey('processes.id'), primary_key=True)
    fk_descendant = db.Column(db.Integer, db.ForeignKey('processes.id'), primary_key=True)

class Process(db.Base):
    __tablename__ = 'processes'
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=datetime.datetime.now)
    id = db.Column(db.Integer, primary_key = True)

    jobid = db.Column(db.String, db.ForeignKey('jobs.jobid'))
    job = db.relationship('Job', back_populates='processes')

    start = db.Column(db.DateTime, default=datetime.datetime.now)
    end = db.Column(db.DateTime, default=datetime.datetime.now)
    duration = db.Column(db.Float, default=0)
    tags = db.Column(db.JSON)

    host_id = db.Column(db.String, db.ForeignKey('hosts.name'))
    host = db.relationship('Host', backref="processes")

    threads_df = db.Column(db.JSON)
    threads_sums = db.Column(db.JSON)
    numtids = db.Column(db.Integer, default=1)
    # exclusive cpu time
    cpu_time = db.Column(db.Float)
    # sum of cpu times of all descendants + process_cpu_time
    inclusive_cpu_time = db.Column(db.Float)
    exename = db.Column(db.String)
    path = db.Column(db.String)
    args = db.Column(db.String)
    pid = db.Column(db.Integer)
    ppid = db.Column(db.Integer)
    pgid = db.Column(db.Integer)
    sid = db.Column(db.Integer)
    gen = db.Column(db.Integer)
    exitcode = db.Column(db.Integer)
    # for creating a process graph
    # a child process is also included in the list of descendants
    # while parent is included in the ancestors
    parent_id = db.Column(db.Integer, db.ForeignKey('processes.id'))
    children= db.relationship('Process', backref=db.backref('parent', remote_side=[id]))
    ancestors = db.relationship('ProcessAssociation',backref='descendants', primaryjoin=id==ProcessAssociation.fk_ancestor)
    descendants = db.relationship('ProcessAssociation',backref='ancestors', primaryjoin=id==ProcessAssociation.fk_descendant )
