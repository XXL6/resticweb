import logging
from threading import Thread
from time import sleep
from resticweb.dictionary.resticweb_constants import JobStatus, JobStatusFinished
from resticweb.models.general import JobHistory
from datetime import datetime
from resticweb.tools.local_session import LocalSession
from resticweb.interfaces.repository_list import add_repository
from os import path
from datetime import datetime
import json



# purpose of this class is to grab job objects from the job queue
# and submit them for execution in the process manager.
# It also stores the job in the job history after completion;
class JobRunner(Thread):

    def __init__(self, queue, process_manager):
        super().__init__(daemon=True)
        self.queue = queue
        self.process_manager = process_manager
        self.logger = logging.getLogger("mainLogger")
        # sometimes the process might report its' status as finished and
        # then the process will terminate, but the elif statements might
        # already be past the 'status' == 'success' for example and will
        # fall under the 'not alive' statement and it will think that the
        # process quit before it was able to report its status.
        # we can mitigate this by setting a timer to give the job plenty of time
        # to finish
        self.dead_process_timeout = 30 # in seconds

    # at the moment only one job gets run at a time with no concurrency
    # once it finishes, the next job is run
    # does not check whether or not a job can be run at this time
    # and will attempt to do it regardless
    def run(self):
        while True:
            job = self.queue.peek()
            if job:
                if job.status == JobStatus.JOB_STATUS_QUEUED:
                    self.process_manager.add_process(job.process)
                    job.time_started = datetime.now()
                    job.status = JobStatus.JOB_STATUS_RUNNING
                elif job.status == JobStatus.JOB_STATUS_RUNNING:
                    if job.process.data.get('status') == 'success':
                        self.add_to_history(
                            name=job.name,
                            status=JobStatusFinished.JOB_STATUS_SUCCESS,
                            type=type(job.process).__name__,
                            # log='\n'.join(job.process.log),
                            log=json.dumps(job.process.job_log),
                            
                            time_started=job.time_started,
                            time_finished=datetime.now(),
                            result=job.process.data.get('result')
                        )
                        if job.success_callback is not None:
                            job.success_callback(job)
                        job.status = JobStatus.JOB_STATUS_FINISHED
                    elif job.process.data.get('status') == 'error':
                        self.add_to_history(
                            name=job.name,
                            status=JobStatusFinished.JOB_STATUS_ERROR,
                            type=type(job.process).__name__,
                            # log='\n'.join(job.process.log),
                            log=json.dumps(job.process.job_log),
                            time_started=job.time_started,
                            time_finished=datetime.now()
                        )
                        if job.error_callback is not None:
                            job.error_callback()
                        job.status = JobStatus.JOB_STATUS_FINISHED
                    elif job.process.data.get('status') == 'warning':
                        self.add_to_history(
                            name=job.name,
                            status=JobStatusFinished.JOB_STATUS_WARNING,
                            type=type(job.process).__name__,
                            # log='\n'.join(job.process.log),
                            log=json.dumps(job.process.job_log),
                            time_started=job.time_started,
                            time_finished=datetime.now()
                        )
                        if job.warning_callback is not None:
                            job.warning_callback()
                        job.status = JobStatus.JOB_STATUS_FINISHED
                    elif not job.process.is_alive() and job.timeout_start is None and (job.process.data.get('status') == 'running' or job.process.data.get('status') is None):
                        job.timeout_start = datetime.now()
                    elif job.timeout_start and (datetime.now() - job.timeout_start).seconds > self.dead_process_timeout:
                        job.process.job_log.append("Job's process exited with no status.")
                        self.add_to_history(
                            name=job.name,
                            status=JobStatusFinished.JOB_STATUS_WARNING,
                            type=type(job.process).__name__,
                            # log='\n'.join(job.process.log),
                            log=json.dumps(job.process.job_log),
                            time_started=job.time_started,
                            time_finished=datetime.now()
                        )
                        job.status = JobStatus.JOB_STATUS_FINISHED
                elif job.status == JobStatus.JOB_STATUS_FINISHED:
                    # self.post_run_routine(self.queue.pop())
                    self.queue.pop()
            sleep(5)

    def add_to_history(self, **kwargs):
        try:
            elapsed = kwargs.get('time_finished') - kwargs.get('time_started')
            elapsed = (datetime.min + elapsed).time()
            history = JobHistory(
                name=kwargs.get('name'),
                status=kwargs.get('status'),
                type=kwargs.get('type'),
                log=kwargs.get('log'),
                time_started=kwargs.get('time_started'),
                time_finished=kwargs.get('time_finished'),
                time_elapsed=elapsed,
                result=json.dumps(kwargs.get('result'))
            )
            with LocalSession() as session:
                session.add(history)
                session.commit()
        except Exception:
            pass
