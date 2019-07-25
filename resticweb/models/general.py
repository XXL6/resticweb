from datetime import datetime
from resticweb import db
from sqlalchemy.types import JSON as JSONType


class SysVars(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'sys_vars'
    id = db.Column(db.Integer, primary_key=True)
    # JSON might be better but SQLite doesn't seem to support it
    var_name = db.Column(db.String(100), nullable=False)
    var_data = db.Column(db.String(100), nullable=True)


class CredentialStore(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'credential_store'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer, db.ForeignKey('credential_group.id'), nullable=False)
    credential_role = db.Column(db.String(100), nullable=False)
    credential_data = db.Column(db.String(100))


class CredentialGroup(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'credential_group'
    id = db.Column(db.Integer, primary_key=True)
    credentials = db.relationship(
        'CredentialStore', backref='credential_group', lazy='subquery')
    description = db.Column(db.String(100))
    service_name = db.Column(db.String(50), nullable=False)
    service_id = db.Column(db.String(50))
    time_added = db.Column(
                        db.DateTime,
                        nullable=False,
                        default=datetime.utcnow)


class SavedJobs(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'saved_jobs'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String, nullable=False, unique=True, index=True)
    notes = db.Column(db.Text)
    engine_class = db.Column(db.String(50), nullable=False, index=True)

    time_added = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow)
    
    history = db.relationship('JobHistory', backref='saved_job', lazy=True)
    parameters = db.relationship('JobParameter', backref='saved_job', lazy=True)


class JobParameter(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'job_parameter'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    param_name = db.Column(db.String(50), nullable=False, index=True)
    param_display_name = db.Column(db.String(50))
    param_value = db.Column(db.Text)

    job_id = db.Column(db.Integer, db.ForeignKey('saved_jobs.id'), nullable=False)


class JobHistory(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'job_history'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String, nullable=False, index=True)
    log = db.Column(db.Text)
    result = db.Column(db.Text)
    time_started = db.Column(db.DateTime)
    time_finished = db.Column(db.DateTime)
    time_elapsed = db.Column(db.Time)
    time_added = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow)

    saved_job_id = db.Column(db.Integer, db.ForeignKey('saved_jobs.id'), nullable=True)


class Repository(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'repository'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    internal_name = db.Column(db.String, index=True)
    repo_id = db.Column(db.String)
    description = db.Column(db.Text)
    cache_repo = db.Column(db.Boolean, default=False)
    credential_group_id = db.Column(db.Integer)
    data = db.Column(db.Text)
    address = db.Column(db.String)
    repository_type_id = db.Column(db.Integer, db.ForeignKey('repository_type.id'), nullable=False)
    time_added = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow)

    snapshots = db.relationship("Snapshot",
            backref='repository',
            cascade="all, delete, delete-orphan",
            lazy=True)



class RepositoryType(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'repository_type'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, unique=True)
    type = db.Column(db.String(15), nullable=False)  # cloud, local, offsite
    description = db.Column(db.Text)

    repositories = db.relationship(
        'Repository',
        backref='repository_type',
        cascade="all, delete, delete-orphan",
        lazy=True
    )


class BackupSet(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'backup_set'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, unique=True)
    type = db.Column(db.Integer, nullable=False)
    data = db.Column(db.Text)
    source = db.Column(db.String, nullable=True)

    time_added = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    backup_objects = db.relationship(
        'BackupObject',
        back_populates='backup_set',
        cascade="all, delete, delete-orphan",
        lazy=True
    )


class BackupObject(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'backup_object'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    data = db.Column(db.Text)
    time_added = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    backup_set_id = db.Column(db.Integer, db.ForeignKey('backup_set.id'))
    backup_set = db.relationship("BackupSet", back_populates="backup_objects")


# object contained within the snapshot
class SnapshotObject(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'snapshot_object' 
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(150), index=True)
    type = db.Column(db.String)
    path = db.Column(db.String)
    uid = db.Column(db.Integer)
    gid = db.Column(db.Integer)
    size = db.Column(db.Integer)
    mode = db.Column(db.Integer)
    struct_type = db.Column(db.String(50))
    modified_time = db.Column(db.DateTime)
    accessed_time = db.Column(db.DateTime)
    created_time = db.Column(db.DateTime)
    
    snapshot = db.relationship("Snapshot", back_populates="snapshot_objects")

    snapshot_id = db.Column(db.String(200), db.ForeignKey('snapshot.snap_id'))

    def to_dict(self):
        return dict(
            id=self.id,
            name=self.name,
            type=self.type,
            path=self.path,
            uid=self.uid,
            gid=self.gid,
            size=self.size,
            mode=self.mode,
            struct_type=self.struct_type,
            modified_time=self.modified_time,
            accessed_time=self.accessed_time,
            created_time=self.created_time
        )


class Snapshot(db.Model):
    __bind_key__ = 'general'
    __tablename__ = 'snapshot' 
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    data = db.Column(db.String)
    snap_id = db.Column(db.String(64), nullable=False, index=True)
    snap_short_id = db.Column(db.String(8))
    snap_time = db.Column(db.DateTime)
    paths = db.Column(db.Text)
    hostname = db.Column(db.String(100))
    username = db.Column(db.String(100))
    tree = db.Column(db.String(64))

    snapshot_objects = db.relationship(
        'SnapshotObject',
        back_populates='snapshot',
        cascade="all, delete, delete-orphan",
        lazy=True
    )

    repository_id = db.Column(db.Integer, db.ForeignKey('repository.id'))

    def to_dict(self):
        return dict(
            id=self.id,
            data=self.data,
            snap_id=self.snap_id,
            snap_short_id=self.snap_short_id,
            snap_time=self.snap_time,
            paths=self.paths,
            hostname=self.hostname,
            username=self.username,
            tree=self.tree
        )

