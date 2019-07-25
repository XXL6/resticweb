from resticweb.tools.local_session import LocalSession
from resticweb.dictionary.resticweb_constants import JobStatus
from resticweb.models.general import JobHistory


def get_jobs(type=None):
    jobs = []
    with LocalSession() as session:
        if not type:
            job_list = session.query(JobHistory)
        else:
            job_list = session.query(JobHistory).filter_by(type=type)
        for job in job_list:
            jobs.append(job)
    return jobs


def get_job(id):
    with LocalSession() as session:
        job = session.query(JobHistory).filter_by(id=id).first()
    return job


def delete_jobs(ids):
    with LocalSession() as session:
        for id in ids:
            session.query(JobHistory).filter_by(id=id).delete()
        session.commit()