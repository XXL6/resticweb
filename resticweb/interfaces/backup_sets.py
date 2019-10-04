from resticweb.models.general import BackupSet, BackupObject, JobParameter
from resticweb.tools.local_session import LocalSession
from resticweb.dictionary.resticweb_constants import BackupSetList, BackupSetTypes
import platform
import json


def delete_backup_set(id):
    with LocalSession() as session:
        temp = session.query(BackupSet).filter_by(id=id).first()
        job_parameters = session.query(JobParameter).filter_by(param_name='backup_set', param_value=temp.id)
        for param in job_parameters:
            param.param_value = None
        session.delete(temp)
        session.commit()


def delete_backup_sets(ids):
    with LocalSession() as session:
        for id in ids:
            temp = session.query(BackupSet).filter_by(id=id).first()
            job_parameters = session.query(JobParameter).filter_by(param_name='backup_set', param_value=temp.id)
            for param in job_parameters:
                param.param_value = None
            session.delete(temp)
        session.commit()


def get_backup_sets():
    with LocalSession() as session:
        backup_sets = session.query(BackupSet)
        return_list = []
        for backup_set in backup_sets:
            return_list.append(
                dict(
                    id=backup_set.id,
                    name=backup_set.name,
                    type=BackupSetList.BACKUP_SETS[backup_set.type]
                )
            )
        return return_list

# used for getting a tuple of values to be added to a select field
# on a form
def get_backup_sets_tuple():
    with LocalSession() as session:
        backup_sets = session.query(BackupSet)
        return_list = []
        for backup_set in backup_sets:
            return_list.append(
                (backup_set.id, backup_set.name)
            )
        return return_list


def add_backup_set(data):
    with LocalSession() as session:
        if data['type'] == BackupSetTypes.BS_TYPE_FILESFOLDERS:
            json_object = json.loads(data['backup_object_data']['file_data'])
            backup_object_list = json_object['file_list']
            display_state = json.dumps(json_object['state'])
        else: 
            raise Exception(f"Unsupported backup set {data['type']}")
        backup_set = (
            BackupSet(
                name=data['name'],
                type=data['type'],
                source=data['source'],
                concurrent_uses=data['concurrent_uses'],
                timeout=data['timeout'],
                data=display_state
            )
        )
        session.add(backup_set)
        session.commit()
        if platform.system() == 'Windows':
            remove_trailing_slash = True
        else:
            remove_trailing_slash = False
        for backup_object in backup_object_list:
            if remove_trailing_slash:
                backup_object = backup_object[:1] + backup_object[2:]
            new_backup_object = BackupObject(
                data=backup_object,
                backup_set_id=backup_set.id)
            session.add(new_backup_object)
        session.commit()


def update_backup_set(data):
    with LocalSession() as session:
        current_set = session.query(BackupSet).filter_by(id=data['id']).first()
        if current_set.type == BackupSetTypes.BS_TYPE_FILESFOLDERS:
            json_object = json.loads(data['backup_object_data']['file_data'])
            backup_object_list = json_object['file_list']
            display_state = json.dumps(json_object['state'])
        else: 
            raise Exception(f"Unsupported backup set {data['type']}")
        if current_set.name != data['name']:
            current_set.name = data['name']
        if current_set.source != data['source']:
            current_set.source = data['source']
        if current_set.concurrent_uses != data['concurrent_uses']:
            current_set.concurrent_uses = data['concurrent_uses']
        if current_set.timeout != data['timeout']:
            current_set.timeout = data['timeout']
        current_set.data = display_state
        if platform.system() == 'Windows':
            backup_object_list[:] = [backup_object[:1] + backup_object[2:] for backup_object in backup_object_list]
        existing_backup_object_list = session.query(BackupObject).filter_by(backup_set_id=current_set.id)
        for existing_backup_object in existing_backup_object_list:
            try:
                backup_object_list.index(existing_backup_object.data)
            except ValueError:
                session.delete(existing_backup_object)
        for backup_object in backup_object_list:
            existing_backup_object = session.query(BackupObject).filter_by(backup_set_id=current_set.id, data=backup_object).first()
            if not existing_backup_object:
                new_backup_object = BackupObject(
                    data=backup_object,
                    backup_set_id=current_set.id)
                session.add(new_backup_object)
        session.commit()


def get_backup_set_objects(id):
    with LocalSession() as session:
        backup_set_object_list = session.query(BackupObject).filter_by(backup_set_id=id).all()
        return_list = []
        for backup_object in backup_set_object_list:
            return_list.append(backup_object.data)
    return return_list


def get_backup_set_info(id, include_backup_objects=True):
    with LocalSession() as session:
        backup_set = session.query(BackupSet).filter_by(id=id).first()
        if include_backup_objects:
            set_item_list = session.query(BackupObject).filter_by(backup_set_id=id)
            set_item_list_data = []
            for item in set_item_list:
                set_item_list_data.append(item.data)
        if backup_set:
            info_dict = dict(
                id=backup_set.id,
                name=backup_set.name,
                source=backup_set.source,
                type_name=BackupSetList.BACKUP_SETS[backup_set.type],
                data=backup_set.data,
                type=backup_set.type,
                time_added=backup_set.time_added,
                concurrent_uses=backup_set.concurrent_uses,
                timeout=backup_set.timeout
            )
        else:
            info_dict = dict(
                id="UNDEFINED",
                name="UNDEFINED",
                source="UNDEFINED",
                type_name="UNDEFINED",
                type="UNDEFINED",
                time_added="UNDEFINED",
                concurrent_uses=0,
                timeout=0
            )
        if include_backup_objects:
            return info_dict, set_item_list_data
        else:
            return info_dict
