from resticweb.models.general import Repository, Snapshot, SnapshotObject
from resticweb.tools.local_session import LocalSession
import resticweb.interfaces.repository_list as repository_list_interface
from resticweb.interfaces.repository_formatted import ResticRepositoryFormatted
import json

# following methods may not be placed under another "with LocalSession()" block
# following methods sync the objects in an actual repository with the
# objects in the database. They also return the objects in case that's needed
def sync_snapshots(repo_id):
    repo_address = repository_list_interface.get_repository_address(repo_id)
    repo_password = repository_list_interface.get_repository_password(repo_id)
    repo_formatted = ResticRepositoryFormatted(repo_address, repo_password)
    snapshots = repo_formatted.get_snapshots()
    with LocalSession() as session:
        session.query(Snapshot).filter_by(repository_id=repo_id).delete()
        if snapshots:
            for item in snapshots:
                new_snapshot = Snapshot(
                        snap_id=item.get('snap_id'),
                        snap_short_id=item.get('snap_short_id'),
                        snap_time=item.get('snap_time'),
                        hostname=item.get('hostname'),
                        username=item.get('username'),
                        tree=item.get('tree'),
                        repository_id=repo_id,
                        paths=json.dumps(item.get('paths'))
                )
                session.add(new_snapshot)
            session.commit()
    return snapshots

def sync_repository_info(repo_id):
    repository_list_interface.get_info(repo_id)

def sync_snapshot_objects(repo_id, snapshot_id):
    repo_address = repository_list_interface.get_repository_address(repo_id)
    repo_password = repository_list_interface.get_repository_password(repo_id)
    repo_formatted = ResticRepositoryFormatted(repo_address, repo_password)
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