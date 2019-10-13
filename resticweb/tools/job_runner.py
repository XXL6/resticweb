import logging
from threading import Thread
from time import sleep
from resticweb.dictionary.resticweb_constants import JobStatus



# purpose of this class is to grab job objects from the job queue
# and submit them for execution in the process manager.
# It also stores the job in the job history after completion;
class JobRunner(Thread):

    def __init__(self, queue):#, process_manager, resource_manager):
        super().__init__(daemon=True)
        self.queue = queue
        # self.process_manager = process_manager
        # self.resource_manager = resource_manager
        self.logger = logging.getLogger("mainLogger")

    # the job runner will iterate through the queue and will attempt to
    # start each job one by one. If a job cannot acquire resources at the time,
    # the runner will move on to the next job to start
    def run(self):
        while True:
            # job = self.queue.peek()
            for job in self.queue.get_queue_list():
            # if job:
                job.check_status()
                if (job.status == JobStatus.JOB_STATUS_QUEUED or
                    job.status == JobStatus.JOB_STATUS_ACQUIRING_RESOURCES or
                    job.status == JobStatus.JOB_STATUS_WAITING_RESOURCES):
                        job.start()                    
                elif job.status == JobStatus.JOB_STATUS_FINISHED:
                    # self.post_run_routine(self.queue.pop())
                    self.queue.remove(job)
            sleep(5)

    

