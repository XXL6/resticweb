from resticweb.models.general import BackupRecord
from resticweb.tools.local_session import LocalSession

def add_record(info_dict):
    new_record = BackupRecord(
        backup_set_id = info_dict['backup_set_id'],
        repository_id = info_dict['repository_id'],
        snapshot_id = info_dict['snapshot_id'],
        files_new = info_dict['files_new'],
        files_changed = info_dict['files_changed'],
        files_unmodified = info_dict['files_unmodified'],
        dirs_new = info_dict['dirs_new'],
        dirs_changed = info_dict['dirs_changed'],
        dirs_unmodified = info_dict['dirs_unmodified'],
        data_blobs = info_dict['data_blobs'],
        tree_blobs = info_dict['tree_blobs'],
        data_added = info_dict['data_added'],
        total_files_processed = info_dict['total_files_processed'],
        total_bytes_processed = info_dict['total_bytes_processed']
    )

    with LocalSession() as session:
        session.add(new_record)
        session.commit()

def delete_record(id):
    with LocalSession() as session:
        record = session.query(BackupRecord).filter_by(id=id).first()
        session.delete(record)
        session.commit()