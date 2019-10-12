from resticweb.models.general import BackupRecord
from resticweb.tools.local_session import LocalSession
import logging

logger = logging.getLogger('mainlogger')


def add_record(info_dict):
    new_record = BackupRecord(
        backup_set_id = info_dict['backup_set_id'],
        repository_id = info_dict['repository_id'],
        snapshot_id = info_dict['snapshot_id']
        #files_new = info_dict['files_new'],
        #files_changed = info_dict['files_changed'],
        #files_unmodified = info_dict['files_unmodified'],
        #dirs_new = info_dict['dirs_new'],
        #dirs_changed = info_dict['dirs_changed'],
        #dirs_unmodified = info_dict['dirs_unmodified'],
        #data_blobs = info_dict['data_blobs'],
        #tree_blobs = info_dict['tree_blobs'],
        #data_added = info_dict['data_added'],
        #total_files_processed = info_dict['total_files_processed'],
        #total_bytes_processed = info_dict['total_bytes_processed']
    )

    with LocalSession() as session:
        session.add(new_record)
        session.commit()

def delete_record(id):
    with LocalSession() as session:
        try:
            record = session.query(BackupRecord).filter_by(id=id).first()
            session.delete(record)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to delete Backup Record with id {id}. Reason {e}")


def delete_record_by_snap_id(repository_id, snapshot_id):
    with LocalSession() as session:
        try:
            record = session.query(BackupRecord).filter_by(repository_id=repository_id, snapshot_id=snapshot_id).first()
            session.delete(record)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to delete Backup Record with snapshot_id {snapshot_id}. Reason {e}")


def delete_records_by_repo_id(repository_id):
    with LocalSession() as session:
        try:
            records = session.query(BackupRecord).filter_by(repository_id=repository_id).all()
            for record in records:
                session.delete(record)
        except Exception as e:
            logger.error(f"Failed to delete all Backup Records with repository_id {repository_id}. Reason {e}")