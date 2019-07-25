from resticweb.tools.local_session import LocalSession
from resticweb.models.general import SavedJobs, JobParameter, Repository, BackupObject
from resticweb.tools import job_tools
from resticweb.misc import job_queue
from resticweb.misc.credential_manager import credential_manager
from resticweb.engine_classes.class_name_map import get_class_from_name
import resticweb.tools.job_callbacks as job_callbacks
from resticweb.dictionary.resticweb_variables import Config

def delete_jobs(ids):
    with LocalSession() as session:
        for id in ids:
            session.query(SavedJobs).filter_by(id=id).delete()
        session.commit()


def add_job(info):
    with LocalSession() as session:
        jobs = SavedJobs(
            name=info['name'],
            notes=info.get('notes'),
            engine_class=info['engine_class']
        )
        session.add(jobs)
        session.commit()
        for key, value in info.get('params').items():
            parameter = JobParameter(
                param_name=key,
                param_value=value,
                job_id=jobs.id
            )
            session.add(parameter)
        session.commit()
        return jobs.id

def update_job(info):
    with LocalSession() as session:
        job = session.query(SavedJobs).filter_by(id=info['saved_job_id']).first()
        job.name = info['name']
        job.notes = info['notes']
        session.commit()
        another_commit = False
        # this will just update the existing parameters
        # if a new parameter is passed in through the info dictionary argument
        # it will not be added at this time
        if info.get('params'):
            for param in job.parameters:
                if info['params'].get(param.param_name) != param.param_value:
                    param.param_value = info['params'].get(param.param_name)
                    another_commit = True
        if another_commit:
            session.commit()


def get_job_info(id):
    with LocalSession() as session:
        job = session.query(SavedJobs).filter_by(id=id).first()
        if job:
            info_dict = dict(
                name=job.name,
                notes=job.notes,
                engine_class=job.engine_class,
                params=job.params,
                last_attempted_run=job.last_attempted_run,
                last_successful_run=job.last_successful_run,
                time_added=job.time_added
            )
            return info_dict


def update_job_times(id, info):
    with LocalSession() as session:
        job = session.query(SavedJobs).filter_by(id=id).first()
        if info.get('last_attempted_run'):
            job.last_attempted_run = info['last_attempted_run']
        if info.get('last_successful_run'):
            job.last_successful_run = info['last_successful_run']
        session.commit()


def run_saved_job_backup(id, background=True):
    with LocalSession() as session:
        job = session.query(SavedJobs).filter_by(id=id).first()
        job_class = get_class_from_name(job.engine_class)
        parameter_dictionary = {}
        for parameter in job.parameters:
            parameter_dictionary[parameter.param_name] = parameter.param_value
        repository = session.query(Repository).filter_by(id=parameter_dictionary['repository']).first()
        repo_password = credential_manager.get_group_credentials(repository.credential_group_id).get('repo_password')
        repo_address = repository.address
        backup_objects = session.query(BackupObject).filter_by(backup_set_id=parameter_dictionary['backup_set'])
        object_list = [bak_object for bak_object in backup_objects]
        process_object = job_class(address=repo_address, repo_password=repo_password, object_list=object_list, engine_location=Config.ENGINE_COMMAND)
        job_object = job_tools.JobObject(name=job.name, process=process_object)
        job_object.success_callback = job_callbacks.test_backup_callback
        if background:
            job_queue.add(job=job_object)
        else:
            job_object.process.run()