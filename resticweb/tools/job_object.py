from resticweb import process_manager
from resticweb.misc import resource_manager
import traceback
from datetime import datetime
from resticweb.dictionary.resticweb_exceptions import JobQueueFullException, ResourceGeneralException, ResourceUnavailable, ResourceOffline
from resticweb.dictionary.resticweb_constants import JobStatus, JobStatusMap, JobStatusFinished
from resticweb.dictionary.resticweb_constants import System
from resticweb.tools.local_session import LocalSession
from resticweb.models.general import JobHistory
import json
import logging

class JobObject:
    logger = logging.getLogger('debugLogger')
    def __init__(self, **kwargs):
        self.name = kwargs['name']
        self.process = kwargs['process']
        self.type = type(self.process).__name__

        self.time_started = datetime.min
        self.time_finished = datetime.min
        # id gets assigned when job object is added to the queue
        self.id = -1
        # all new jobs will begin life as queued and will
        # change as they are processed by the job runner
        self.status = JobStatus.JOB_STATUS_QUEUED
        self.finished_status = None
        # list of resources that the job object should request before
        # being able to be run: {'resource_type', 'resource_id', 'amount'}
        self.resources = kwargs.get('resources')
        if not self.resources:
            self.resources = []
        self.acquired_resources = []
        # how long can the job stay in the queue after the process
        # within it has finished. Useful in case the process finishes but
        # it doesn't report it's status for some reason. Then the job doesn't
        # stay in the queue forever
        self.timeout_start = None
        self.resource_timeout_start = None
        # the lowest timeout amount from each resource. Once the
        # resource_timeout_start and current time difference goes above the
        # min resource timeout, the job should be discarded with an error
        self.min_resource_timeout = None
        
        self.success_callback = None
        self.warning_callback = None
        self.error_callback = None

        self.resource_unavailable_callback = None
        self.resource_offline_callback = None

    def acquire_resources(self):
        acquisition_successfull = True
        if self.status is not JobStatus.JOB_STATUS_WAITING_RESOURCES:
            self.status = JobStatus.JOB_STATUS_ACQUIRING_RESOURCES
        if self.timed_out():
            if self.error_callback:
                self.error_callback(self)
            self.finished_status = JobStatusFinished.JOB_STATUS_ERROR
            self.process.job_log.append("Were not able to acquire the required resources within the alloted time.")
            self.finish_job()
        for resource in self.resources:
            try:
                resource_token = resource_manager.checkout(resource_type=resource['resource_type'],
                                    resource_id=resource['resource_id'],
                                    amount=resource['amount'],
                                    exclusive=True if resource['amount'] == -1 else False,
                                    source=self.name)
                self.acquired_resources.append(resource_token)
            except ResourceUnavailable:
                self.resource_offline_or_unavailable(resource)
                self.logger.debug(f"Resource unavailable {resource}")
                if callable(self.resource_unavailable_callback):
                    self.resource_unavailable_callback()
                acquisition_successfull = False
            except ResourceOffline:
                self.resource_offline_or_unavailable(resource)
                if callable(self.resource_offline_callback):
                    self.resource_offline_callback()
                acquisition_successfull = False
            except ResourceGeneralException as e:
                self.cancel_job(f"Exception when acquiring resource: {resource['resource_type']} : {resource['resource_id']} : {e}")
                acquisition_successfull = False
        return acquisition_successfull

    def release_resources(self):
        for resource_token in self.acquired_resources:
            resource_manager.checkin(resource_token)
        self.acquired_resources = []

    def resource_offline_or_unavailable(self, resource):
        timeout = resource_manager.get_availability_timeout(resource['resource_type'], resource['resource_id'])
        if self.min_resource_timeout is None:
            self.min_resource_timeout = timeout
        elif timeout < self.min_resource_timeout:
            self.min_resource_timeout = timeout
        if self.resource_timeout_start is None:
            self.status = JobStatus.JOB_STATUS_WAITING_RESOURCES
            self.resource_timeout_start = datetime.now()
        self.release_resources()

    def timed_out(self):
        return (self.min_resource_timeout) and (((datetime.now() - self.resource_timeout_start).seconds / 60) > self.min_resource_timeout)

    def start(self):
        if self.status != JobStatus.JOB_STATUS_RUNNING or self.status != JobStatus.JOB_STATUS_FINISHED:
            try:
                if self.acquire_resources():
                    process_manager.add_process(self.process)
                    self.time_started = datetime.now()
                    self.status = JobStatus.JOB_STATUS_RUNNING
            except Exception as e:
                self.cancel_job(f'Failed to start job: {e}\n{traceback.format_exc()}')

    def check_status(self):
        status = self.process.data.get('status')
        if status == 'success':
            self.finished_status = JobStatusFinished.JOB_STATUS_SUCCESS
            if self.success_callback:
                self.success_callback(self)
            self.finish_job()
        elif status == 'error':
            if self.error_callback:
                self.error_callback(self)
            self.finished_status = JobStatusFinished.JOB_STATUS_ERROR
            self.finish_job()
        elif status == 'warning':
            if self.warning_callback:
                self.warning_callback(self)
            self.finished_status = JobStatusFinished.JOB_STATUS_WARNING
            self.finish_job()
        elif not self.process.is_alive() and self.timeout_start is None and (status == 'running' or status is None) and self.status not in [JobStatus.JOB_STATUS_QUEUED, JobStatus.JOB_STATUS_WAITING_RESOURCES, JobStatus.JOB_STATUS_ACQUIRING_RESOURCES]:
            self.timeout_start = datetime.now()
        elif self.timeout_start and (datetime.now() - self.timeout_start).seconds > System.DEAD_PROCESS_TIMEOUT:
            if self.warning_callback:
                self.warning_callback(self)
            self.finished_status = JobStatusFinished.JOB_STATUS_WARNING
            self.process.job_log.append("Job's process exited with no status.")
            self.finish_job()

    def finish_job(self):
        self.time_finished = datetime.now()
        self.add_to_history()
        if len(self.acquired_resources) > 0:
            self.release_resources()
        self.status = JobStatus.JOB_STATUS_FINISHED

    def add_to_history(self):
        try:
            try:
                elapsed = self.time_finished - self.time_started
                elapsed = (datetime.min + elapsed).time()
            except TypeError:
                elapsed = datetime.min.time()
                self.time_started = datetime.min.time()
            history = JobHistory(
                name=self.name,
                status=self.finished_status,
                type=self.type,
                log=json.dumps(self.process.job_log),
                time_started=self.time_started,
                time_finished=self.time_finished,
                time_elapsed=elapsed,
                result=json.dumps(self.process.data.get('result'))
            )
            with LocalSession() as session:
                session.add(history)
                session.commit()
        except Exception as e:
            print(e)
            print(traceback.format_exc())
    
    def cancel_job(self, reason=None):
        self.process.data['result'] = "Job was cancelled."
        self.process.data['result'] = f"Reason for cancellation: {reason}"
        self.finished_status = JobStatusFinished.JOB_STATUS_ERROR
        self.finish_job()
