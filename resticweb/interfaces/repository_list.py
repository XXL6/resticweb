import os
# from resticweb.dictionary.resticweb_constants import Repository as Rep
from resticweb.models.general import Repository, Snapshot, SnapshotObject, JobParameter
from resticweb.tools.local_session import LocalSession
from resticweb.misc.credential_manager import credential_manager
# from .repository import ResticRepository
from .repository_formatted import ResticRepositoryFormatted
from resticweb.tools.repository_tools import sync_snapshots, sync_snapshot_objects
import json
from datetime import datetime
from resticweb.dateutil import parser

# repository_add_to_db is used instead of the following method
# it's located under resticweb.tools.job_callbacks
def add_repository(info):
    with LocalSession() as session:
        repository = Repository(
            name=info['name'],
            description=info.get('description'),
            repo_id=info.get('repo_id'),
            address=info['address'],
            data=info.get('data'),
            credential_group_id=info.get('credential_group_id'),
            repository_type_id=info['repository_type_id']
        )
        session.add(repository)
        session.commit()
        return repository.id


def update_repository(info, repo_id, sync_db=False, unsync_db=False):
    with LocalSession() as session:
        repository = session.query(Repository).filter_by(id=repo_id).first()
        if repository.name != info['name']:
            credential_manager.set_service_id(repository.credential_group_id, info['name'])
        repository.name = info['name']
        repository.description = info.get('description')
        repository.address = info['address']
        repository.cache_repo = info['cache_repo']
        session.commit()
        from resticweb.tools.job_build import JobBuilder
        if sync_db:
            job_builder = JobBuilder(job_name=f"Sync repo {repository.name}", job_class='repository_sync', parameters=dict(repository=repository.id))
            job_builder.run_job()
        if unsync_db:
            for snapshot in repository.snapshots:
                session.delete(snapshot)
            session.commit()
    return repo_id


def delete_repositories(ids):
    with LocalSession() as session:
        for id in ids:
            repo_to_remove = session.query(Repository).filter_by(id=id).first()
            credential_manager.remove_credentials(repo_to_remove.credential_group_id)
            job_parameters = session.query(JobParameter).filter_by(param_name='repository', param_value=id).all()
            for parameter in job_parameters:
                parameter.param_value = None
            session.delete(repo_to_remove)
        session.commit()


def get_engine_repositories():
    repository_list = []
    with LocalSession() as session:
        repositories = session.query(Repository).filter_by()
        for repository in repositories:
            repository_list.append((repository.id, repository.name))
    return repository_list


def get_repository_from_snap_id(snap_id):
    with LocalSession() as session:
        snapshot = session.query(Snapshot).filter_by(snap_id=snap_id).first()
        repository = session.query(Repository).filter_by(id=snapshot.repository_id).first()
        return repository


def get_info(id):
    info_dict = {}
    with LocalSession() as session:
        repository = session.query(Repository).filter_by(id=id).first()
        address = repository.address
        repo_password = credential_manager.get_credential(repository.credential_group_id, "repo_password")
        repository_interface = ResticRepositoryFormatted(address, repo_password)
        misc_data = None
        repo_status = repository_interface.is_offline()
        if not repo_status:
            misc_data = repository_interface.get_stats()
            repository.data = json.dumps(misc_data)
            session.commit()
        else:
            try:
                misc_data = json.loads(repository.data)
            except TypeError:
                misc_data = dict(data=repository.data)
            misc_data['status'] = repo_status
        info_dict = dict(
            name=repository.name,
            description=repository.description,
            repo_id=repository.repo_id,
            address=repository.address,
            repository_data=repository.data,
            data=misc_data
        )
    return info_dict

def get_snapshots(id, use_cache=False):
    with LocalSession() as session:
        repository = session.query(Repository).filter_by(id=id).first()
    address = repository.address
    repo_password = credential_manager.get_credential(repository.credential_group_id, "repo_password")
    repository_interface = ResticRepositoryFormatted(address, repo_password)
    snapshots = []
    if repository_interface.is_online() and not use_cache:
        snapshots = repository_interface.get_snapshots()
        if snapshots:
            sync_snapshots(id)
            return snapshots
        else:
            return {}
    else:
        with LocalSession() as session:
            snapshots = session.query(Snapshot).filter_by(repository_id=repository.id).all()
            return snapshots


def insert_snapshots(items, repo_id):
    with LocalSession() as session:
        for item in items:
            item['snap_id'] = item.pop('id')
            item['snap_short_id'] = item.pop('short_id')
            item['snap_time'] = item.pop('time')
            if item['snap_time']:
                main_time = item['snap_time'][:-7]
                extra = item['snap_time'][-6:]
                main_time = main_time + extra
                # item['snap_time'] = datetime.strptime(main_time, "%Y-%m-%dT%H:%M:%S.%f%z")
                item['snap_time'] = parser.parse(main_time)
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


def get_snapshot_objects(snap_id):
    with LocalSession() as session:
        snapshot = session.query(Snapshot).filter_by(snap_id=snap_id).first()
        repository = session.query(Repository).filter_by(id=snapshot.repository_id).first()
    address = repository.address
    repo_password = credential_manager.get_credential(repository.credential_group_id, "repo_password")
    repository_interface = ResticRepositoryFormatted(address, repo_password)
    if repository_interface.is_online():
        # if the repo is online, we can purge the snapshots from db as we will
        # just re-add them fresh from the actual repo
        object_list = repository_interface.get_snapshot_ls(snap_id)
        if repository.cache_repo:
            sync_snapshot_objects(repository.id, snap_id)
        return object_list
    else:
        with LocalSession() as session:
            snapshot_object_list = session.query(SnapshotObject).filter_by(snapshot_id=snap_id).all()
        snapshot_dict_list = [snapshot_object.to_dict() for snapshot_object in snapshot_object_list]
        return snapshot_dict_list


def insert_snapshot_objects(items, snap_id):
    with LocalSession() as session:
        for item in items:
            if item.get('mtime'):
                try:
                    item['mtime'] = parser.parse(item['mtime'])
                except ValueError:
                    item['mtime'] = None
                item['modified_time'] = item.pop("mtime")
            if item.get('atime'):
                try:
                    item['atime'] = parser.parse(item['atime'])
                except ValueError:
                    item['atime'] = None
                item['accessed_time'] = item.pop("atime")
            if item.get('ctime'):
                try:
                    item['ctime'] = parser.parse(item['ctime'])
                except ValueError:
                    item['ctime'] = None
                item['created_time'] = item.pop("ctime")
            new_item = SnapshotObject(
                name=item.get('name'),
                type=item.get('type'),
                path=item.get('path'),
                uid=item.get('uid'),
                gid=item.get('gid'),
                size=item.get('size'),
                mode=item.get('mode'),
                struct_type=item.get('struct_type'),
                modified_time=item.get('modified_time'),
                accessed_time=item.get('accessed_time'),
                created_time=item.get('created_time'),
                snapshot_id=snap_id
            )
            session.add(new_item)
        session.commit()


def get_snapshot_info(id):
    with LocalSession() as session:
        snapshot = session.query(Snapshot).filter_by(snap_id=id).first()
        if snapshot.paths:
            try:
                snapshot.paths = json.loads(snapshot.paths)
            except ValueError:
                pass
        return snapshot


def get_repository_status(id):
    with LocalSession() as session:
        repository = session.query(Repository).filter_by(id=id).first()
        address = repository.address
        repo_password = credential_manager.get_credential(repository.credential_group_id, "repo_password")
        repository_interface = ResticRepositoryFormatted(address, repo_password)
        status = repository_interface.is_online()
        if status is None:
            return "Couldn't get status"
        else:
            if status:
                return "Online"
            else:
                return "Offline"

def get_repository_name(id):
    with LocalSession() as session:
        repository = session.query(Repository).filter_by(id=id).first()
        if repository:
            return repository.name
        else:
            return None


def get_repository_address(id):
    with LocalSession() as session:
        repository = session.query(Repository).filter_by(id=id).first()
        if repository:
            return repository.address
        else:
            return None

def get_repository_password(id):
    with LocalSession() as session:
        repository = session.query(Repository).filter_by(id=id).first()
        if repository:
            return credential_manager.get_credential(repository.credential_group_id, "repo_password")
        else:
            return None

def get_formatted_repository_interface_from_id(id):
    with LocalSession() as session:
        repository = session.query(Repository).filter_by(id=id).first()
        if repository:
            credential_list = credential_manager.get_group_credentials(repository.credential_group_id)
            repo_password = credential_list.pop('repo_password')
            respository_interface = ResticRepositoryFormatted(repository.address, repo_password, credential_list if len(credential_list) > 0 else None)
            return respository_interface
        else:
            return None
