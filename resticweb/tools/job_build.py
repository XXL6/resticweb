from resticweb.misc import job_queue
from resticweb.tools import job_object
from resticweb.models.general import SavedJobs, JobParameter, Repository, BackupObject
from resticweb.tools.local_session import LocalSession
from resticweb.misc.credential_manager import credential_manager
from resticweb.engine_classes.class_name_map import get_class_from_name
import resticweb.tools.job_callbacks as job_callbacks
from resticweb.dictionary.resticweb_variables import Config
from resticweb.interfaces.repository_list import get_formatted_repository_interface_from_id

# this class is meant to consolidate all job creation into one class.
# job parameters get passed in via the parameters argument and are used
# by the construct_job_object methods to create the job object
# the run method then can be called that will process the job object
# and either run the jobs' process directly or add it to the queue
# so that the job runner can take care of it in the background
class JobBuilder():

    # job_class is just the lower-case name of the class to be run
    # kwargs: job_class, parameters, job_name
    # or
    # kwargs: saved_job_id if building job from the saved job table
    def __init__(self, **kwargs):
        saved_job_id = kwargs.get('saved_job_id')
        if saved_job_id:
            self.init_from_db(saved_job_id)
        else:
            self.job_class_name = kwargs['job_class']
            self.job_class = get_class_from_name(kwargs['job_class'])
            # parameter dictionary: {parameter_name: parameter_value, ...}
            self.parameter_dictionary = kwargs['parameters']
            self.job_name = kwargs.get('job_name')
        self.construct_job_object()

    def init_from_db(self, job_id):
        with LocalSession() as session:
            job = session.query(SavedJobs).filter_by(id=job_id).first()
            self.job_class = get_class_from_name(job.engine_class)
            self.job_name = job.name
            self.job_class_name = job.engine_class
            self.parameter_dictionary = {}
            for parameter in job.parameters:
                self.parameter_dictionary[parameter.param_name] = parameter.param_value

    def construct_job_object(self):
        if self.job_class_name == 'backup':
            self.construct_job_object_backup()
        elif self.job_class_name == 'repository':
            self.construct_job_object_repository()
        elif self.job_class_name == 'restore':
            self.construct_job_object_restore()
        elif self.job_class_name == 'check':
            self.construct_job_object_check()
        elif self.job_class_name == 'forget':
            self.construct_job_object_forget()
        elif self.job_class_name == 'prune':
            self.construct_job_object_prune()
        elif self.job_class_name == 'repository_sync':
            self.construct_job_object_repository_sync()
        else:
            return

    def construct_job_object_backup(self):
        repository = get_formatted_repository_interface_from_id(self.parameter_dictionary['repository'])
        if not repository:
            raise Exception("Invalid repository or repository has been deleted")
        with LocalSession() as session:
            backup_objects = session.query(BackupObject).filter_by(backup_set_id=self.parameter_dictionary['backup_set'])
            if not backup_objects:
                raise Exception("Backup set has been deleted or the backup is empty")
            object_list = [bak_object.data for bak_object in backup_objects]
        process_object = self.job_class(repository=repository, object_list=object_list)
        resources = [dict(resource_type='backup_set', resource_id=self.parameter_dictionary['backup_set'], amount=1),
                dict(resource_type='repository', resource_id=self.parameter_dictionary['repository'], amount=1)]
        self.job_object = job_object.JobObject(name=self.job_name, process=process_object, resources=resources)

    def construct_job_object_repository(self):
        from resticweb.interfaces.repository import ResticRepository
        repository_interface = ResticRepository(self.parameter_dictionary['address'], self.parameter_dictionary['repo_password'], self.parameter_dictionary.get('global_credentials'))
        process_object = self.job_class(repository=repository_interface, field_dict=self.parameter_dictionary.get('field_dict'))
        self.job_object = job_object.JobObject(name=self.job_name, process=process_object)
        self.job_object.success_callback = job_callbacks.repository_add_to_db

    def construct_job_object_restore(self):
        repository = get_formatted_repository_interface_from_id(self.parameter_dictionary['repository'].id)
        process_object = self.job_class(repository=repository,
                                        destination_address=self.parameter_dictionary['destination_address'],
                                        object_list=self.parameter_dictionary.get('object_list'),
                                        snapshot_id=self.parameter_dictionary['snapshot_id'])
        resources = [dict(resource_type='repository', resource_id=self.parameter_dictionary['repository'].id, amount=1)]
        self.job_object = job_object.JobObject(name=self.job_name, process=process_object, resources=resources)

    def construct_job_object_forget(self):
        repository = get_formatted_repository_interface_from_id(self.parameter_dictionary['repository'])
        if not repository:
            raise Exception("Invalid repository or repository has been deleted")
        process_object = self.job_class(repository=repository, snapshot_id=self.parameter_dictionary['snapshot_id'])
        self.job_object = job_object.JobObject(name=self.job_name, process=process_object)

    def construct_job_object_check(self):
        repository = get_formatted_repository_interface_from_id(self.parameter_dictionary['repository'])
        if not repository:
            raise Exception("Invalid repository or repository has been deleted")
        process_object = self.job_class(repository=repository)
        resources = [dict(resource_type='repository', resource_id=self.parameter_dictionary['repository'], amount=-1)]
        self.job_object = job_object.JobObject(name=self.job_name, process=process_object, resources=resources)

    def construct_job_object_prune(self):
        repository = get_formatted_repository_interface_from_id(self.parameter_dictionary['repository'])
        if not repository:
            raise Exception("Invalid repository or repository has been deleted")
        process_object = self.job_class(repository=repository)
        resources = [dict(resource_type='repository', resource_id=self.parameter_dictionary['repository'], amount=-1)]
        self.job_object = job_object.JobObject(name=self.job_name, process=process_object, resources=resources)

    def construct_job_object_repository_sync(self):
        repository = get_formatted_repository_interface_from_id(self.parameter_dictionary['repository'])
        if not repository:
            raise Exception("Invalid repository or repository has been deleted")
        process_object = self.job_class(repository=repository, repo_id=self.parameter_dictionary['repository'])
        resources = [dict(resource_type='repository', resource_id=self.parameter_dictionary['repository'], amount=1)]
        self.job_object = job_object.JobObject(name=self.job_name, process=process_object, resources=resources)
        
    def run_job(self, background=True):
        # if the job is set to run in the background, it will just
        # lock up the front end until the job is finished
        # setting background to true will push it to the queue
        # where it will go through the normal run cycle
        if self.job_object:
            if background:
                job_queue.add(job=self.job_object)
            else:
                return self.job_object.process.run()
        else:
            return False