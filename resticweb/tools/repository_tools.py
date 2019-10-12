from resticweb.models.general import Repository, Snapshot, SnapshotObject, BackupRecord, BackupSet
from resticweb.tools.local_session import LocalSession
import resticweb.interfaces.repository_list as repository_list_interface
from resticweb.interfaces.repository_formatted import ResticRepositoryFormatted
import json

# following methods may not be placed under another "with LocalSession()" block
# following methods sync the objects in an actual repository with the
# objects in the database. They also return the objects in case that's needed
def sync_snapshots(repo_id, repository_interface=None):
    if not repository_interface:
        repo_formatted = repository_list_interface.get_formatted_repository_interface_from_id(repo_id)
    else:
        repo_formatted = repository_interface
    snapshots = repo_formatted.get_snapshots()
    with LocalSession() as session:
        session.query(BackupRecord).filter_by(repository_id=repo_id).delete()
        old_snapshots = session.query(Snapshot).filter_by(repository_id=repo_id).all()
        for snapshot in old_snapshots:
            session.delete(snapshot)
            session.commit()
        if snapshots:
            for item in snapshots:
                snap_tags = item.get('tags')
                new_snapshot = Snapshot(
                        snap_id=item.get('snap_id'),
                        snap_short_id=item.get('snap_short_id'),
                        snap_time=item.get('snap_time'),
                        hostname=item.get('hostname'),
                        username=item.get('username'),
                        tree=item.get('tree'),
                        repository_id=repo_id,
                        paths=json.dumps(item.get('paths')),
                        tags=json.dumps(snap_tags)
                )
                session.add(new_snapshot)
                if snap_tags:
                    for snap_tag in snap_tags:
                        backup_set = session.query(BackupSet).filter_by(name=snap_tag).first()
                        if backup_set:
                            new_record = BackupRecord(
                                snapshot_id=item.get('snap_short_id'),
                                snap_time=item['snap_time'],
                                backup_set_id=backup_set.id,
                                repository_id=repo_formatted.resticweb_repo_id
                            )
                            session.add(new_record)
            session.commit()
    return snapshots


def sync_single_snapshot(repo_id, snapshot_id, repository_interface=None):
    if not repository_interface:
        repo_formatted = repository_list_interface.get_formatted_repository_interface_from_id(repo_id)
    else:
        repo_formatted = repository_interface
    snapshot = repo_formatted.get_snapshots(snapshot_id=snapshot_id)[0]
    with LocalSession() as session:
        existing_snap = session.query(Snapshot).filter_by(repository_id=repo_id, snap_short_id=snapshot_id).first()
        if existing_snap:
            session.delete(existing_snap)
            session.query(BackupRecord).filter_by(repository_id=repo_id, snapshot_id=snapshot_id).delete()
            session.commit()
        if snapshot:
            snap_tags = snapshot.get('tags')
            new_snapshot = Snapshot(
                    snap_id=snapshot.get('snap_id'),
                    snap_short_id=snapshot.get('snap_short_id'),
                    snap_time=snapshot.get('snap_time'),
                    hostname=snapshot.get('hostname'),
                    username=snapshot.get('username'),
                    tree=snapshot.get('tree'),
                    repository_id=repo_id,
                    paths=json.dumps(snapshot.get('paths')),
                    tags=json.dumps(snap_tags)
            )
            session.add(new_snapshot)
            if snap_tags:
                for snap_tag in snap_tags:
                    backup_set = session.query(BackupSet).filter_by(name=snap_tag).first()
                    if backup_set:
                        new_record = BackupRecord(
                            snapshot_id=snapshot.get('snap_short_id'),
                            snap_time=snapshot['snap_time'],
                            backup_set_id=backup_set.id,
                            repository_id=repo_formatted.resticweb_repo_id
                        )
                        session.add(new_record)
            session.commit()
    return snapshot


def sync_repository_info(repo_id, repository_interface=None):
        repository_list_interface.get_info(id=repo_id, repository_interface=repository_interface)

def sync_snapshot_objects(snapshot_id, repo_id, repository_interface=None):
    if not repository_interface:
        repo_formatted = repository_list_interface.get_formatted_repository_interface_from_id(repo_id)
    else:
        repo_formatted = repository_interface
    snapshot_objects = repo_formatted.get_snapshot_ls(snapshot_id)
    with LocalSession() as session:
        for snapshot_object in snapshot_objects:
            new_snapshot_object = SnapshotObject(
                name=snapshot_object.get('name'),
                type=snapshot_object.get('type'),
                path=snapshot_object.get('path'),
                uid=snapshot_object.get('uid'),
                gid=snapshot_object.get('gid'),
                size=snapshot_object.get('size'),
                mode=snapshot_object.get('mode'),
                struct_type=snapshot_object.get('struct_type'),
                modified_time=snapshot_object.get('modified_time'),
                accessed_time=snapshot_object.get('accessed_time'),
                created_time=snapshot_object.get('created_time'),
                snapshot_id=snapshot_id
            )
            session.add(new_snapshot_object)
        session.commit()
    return snapshot_objects


def clear_snapshot_objects(repo_id, snapshot_id):
    with LocalSession() as session:
        snapshot = session.query(Snapshot).filter_by(repository_id=repo_id, snap_short_id=snapshot_id)
        snapshot.snapshot_objects = []
        session.commit()


def clear_repo_snapshot_objects(repo_id):
    with LocalSession() as session:
        snapshots = session.query(Repository).filter_by(id=repo_id).first().snapshots
        for snapshot in snapshots:
            snapshot.snapshot_objects = []
        session.commit()
