import os
# from resticweb.dictionary.resticweb_constants import Repository as Rep
from resticweb.models.general import Repository, Snapshot, SnapshotObject, JobParameter, RepositoryType
from resticweb.tools.local_session import LocalSession
from resticweb.misc.credential_manager import credential_manager
# from .repository import ResticRepository
from .repository_formatted import ResticRepositoryFormatted
from resticweb.tools.repository_tools import sync_snapshots, sync_snapshot_objects, sync_single_snapshot
import json
import traceback
from datetime import datetime
from resticweb.dateutil import parser
import logging

logger = logging.getLogger('debugLogger')

# repository_add_to_db is used instead of the following method
# it's located under resticweb.tools.job_callbacks
def add_repository(info):
    with LocalSession() as session:
        repository = Repository(
            name=info['name'],
            description=info.get('description'),
            repo_id=info.get('repo_id'),
            address=info['address'],
            parameters=info['parameters'],
            data=info.get('data'),
            credential_group_id=info.get('credential_group_id'),
            repository_type_id=info['repository_type_id'],
            concurrent_uses=info.get('concurrent_uses'),
            timeout=info.get('timeout')
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
        repository.concurrent_uses = info['concurrent_uses']
        repository.timeout = info['timeout']
        repository.parameters = json.dumps(info['parameters'])
        session.commit()
        from resticweb.tools.job_build import JobBuilder
        if sync_db:
            job_builder = JobBuilder(job_name=f"Sync repo {repository.name}", job_class='repository_sync', parameters=dict(repository=repository.id, sync_type='full'))
            job_builder.run_job()
        if unsync_db:
            '''
            for snapshot in repository.snapshots:
                snapshot.snapshot_objects = []
            session.commit()
            '''
            job_builder = JobBuilder(job_name=f'Clear db from repo {repository.name}', job_class='clear_snapshot_objects', parameters=dict(repo_id=repository.id))
            job_builder.run_job()
    return repo_id


def delete_repositories(ids):
    credential_groups = []
    with LocalSession() as session:
        for id in ids:
            repo_to_remove = session.query(Repository).filter_by(id=id).first()
            # credential_manager.remove_credentials(repo_to_remove.credential_group_id)
            credential_groups.append(repo_to_remove.credential_group_id)
            job_parameters = session.query(JobParameter).filter_by(param_name='repository', param_value=id).all()
            for parameter in job_parameters:
                parameter.param_value = None
            session.delete(repo_to_remove)
        session.commit()
    for id in credential_groups:
        credential_manager.remove_credentials(id)


def get_repository_from_snap_id(snap_id):
    with LocalSession() as session:
        snapshot = session.query(Snapshot).filter_by(snap_id=snap_id).first()
        repository = session.query(Repository).filter_by(id=snapshot.repository_id).first()
        return repository


# gets basic info about the repository from the database. Also grabs the stats
# from the repository itself like the total size and number of files.
# if use_cache is set to False then the repo stats are grabbed from repo itself
# which might take a bit of time
def get_info(id, repository_interface=None, use_cache=False):
    info_dict = {}
    misc_data = None
    if not repository_interface:
        repository_interface = get_formatted_repository_interface_from_id(id)
    repo_status = repository_interface.is_offline()
    if not use_cache:
        if not repo_status:
            misc_data = repository_interface.get_stats()
    with LocalSession() as session:
        repository = session.query(Repository).filter_by(id=id).first()
        repository_type = session.query(RepositoryType).filter_by(id=repository.repository_type_id).first()
        if misc_data:
            repository.data = json.dumps(misc_data)
            session.commit()
        else:
            try:
                misc_data = json.loads(repository.data)
            except TypeError:
                misc_data = dict(data=repository.data)
            misc_data['status'] = repo_status
        info_dict = dict(
            id=repository.id,
            name=repository.name,
            description=repository.description,
            repo_id=repository.repo_id,
            address=repository.address,
            repository_data=repository.data,
            concurrent_uses=repository.concurrent_uses,
            timeout=repository.timeout,
            data=misc_data,
            cache_repo=repository.cache_repo,
            repository_type=repository_type.name
        )
    return info_dict

# returns a list of snapshots and places them into the database from the
# repository if use_cache is set to False. Returns list of snapshots from
# the database if use_cache is set to True
def get_snapshots(id, use_cache=False):
    repository_interface = get_formatted_repository_interface_from_id(id)
    snapshots = []
    if not use_cache and repository_interface.is_online():
        snapshots = repository_interface.get_snapshots()
        return snapshots if snapshots else {}
    else:
        with LocalSession() as session:
            snapshots = session.query(Snapshot).filter_by(repository_id=id).all()
            return snapshots


def get_snapshot(repo_id, snapshot_id, use_cache=False):
    repository_interface = get_formatted_repository_interface_from_id(repo_id)
    if not use_cache and repository_interface.is_online():
        snapshot = repository_interface.get_snapshots(snapshot_id)[0]
        return snapshot if snapshot else {}
    else:
        with LocalSession() as session:
            snapshot = session.query(Snapshot).filter_by(repository_id=repo_id, snap_short_id=snapshot_id).first()
            return snapshot


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
                paths=json.dumps(item.get('paths')),
                tags=json.dumps(item.get('tags'))
            )
            session.add(new_snapshot)
        session.commit()


def delete_snapshot(repo_id, snapshot_id):
    with LocalSession() as session:
        snapshot = session.query(Snapshot).filter_by(repository_id=repo_id, snap_short_id=snapshot_id).first()
        session.delete(snapshot)
        session.commit()


def get_snapshot_objects(snap_id, use_cache=False):
    with LocalSession() as session:
        snapshot = session.query(Snapshot).filter_by(snap_id=snap_id).first()
        repository = session.query(Repository).filter_by(id=snapshot.repository_id).first()
    repository_interface = get_formatted_repository_interface_from_id(snapshot.repository_id)
    if not use_cache and repository_interface.is_online():
        # if the repo is online, we can purge the snapshots from db as we will
        # just re-add them fresh from the actual repo
        object_list = repository_interface.get_snapshot_ls(snap_id)
        # if repository.cache_repo:
        #    sync_snapshot_objects(repository.id, snap_id, repository_interface=repository_interface)
        return object_list
    else:
        with LocalSession() as session:
            snapshot_object_list = session.query(SnapshotObject).filter_by(snapshot_id=snap_id).all()
        snapshot_dict_list = [snapshot_object.to_dict() for snapshot_object in snapshot_object_list]
        return snapshot_dict_list


def delete_snapshot_objects(snap_id):
    pass


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


def get_engine_repositories():
    repository_list = []
    with LocalSession() as session:
        repositories = session.query(Repository).filter_by()
        for repository in repositories:
            repository_list.append((repository.id, repository.name))
    return repository_list


def get_snapshot_info(id):
    with LocalSession() as session:
        snapshot = session.query(Snapshot).filter_by(snap_id=id).first()
    if snapshot.paths:
        try:
            snapshot.paths = json.loads(snapshot.paths)
        except ValueError:
            pass
    if snapshot.tags:
        try:
            snapshot.tags = json.loads(snapshot.tags)
        except ValueError:
            pass
    return snapshot


def get_repository_status(id):
    repository_interface = get_formatted_repository_interface_from_id(id)
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
    try:
        with LocalSession() as session:
            repository = session.query(Repository).filter_by(id=id).first()
            if repository:
                credential_list = credential_manager.get_group_credentials(repository.credential_group_id)
                if credential_list:
                    repo_password = credential_list.pop('repo_password')
                    respository_interface = ResticRepositoryFormatted(repository.address, repo_password, credential_list if len(credential_list) > 0 else None, id)
                    return respository_interface
    except Exception as e:
        logger.error(e)
        logger.error("trace:" + traceback.format_exc())
    return None
