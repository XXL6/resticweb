from resticweb.tools.local_session import LocalSession
from resticweb.models.general import SavedJobs, JobParameter


def delete_jobs(ids):
    with LocalSession() as session:
        for id in ids:
            session.query(SavedJobs).filter_by(id=id).delete()
            session.query(JobParameter).filter_by(job_id=id).delete()
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


def update_job_times(id, info):
    with LocalSession() as session:
        job = session.query(SavedJobs).filter_by(id=id).first()
        if info.get('last_attempted_run'):
            job.last_attempted_run = info['last_attempted_run']
        if info.get('last_successful_run'):
            job.last_successful_run = info['last_successful_run']
        session.commit()