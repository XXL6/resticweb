from resticweb.misc import job_queue
from resticweb.tools import job_tools
from resticweb.models.general import SavedJobs, JobParameter, Repository, BackupObject
from resticweb.tools.local_session import LocalSession
from resticweb.misc.credential_manager import credential_manager
from resticweb.engine_classes.class_name_map import get_class_from_name
import resticweb.tools.job_callbacks as job_callbacks
from resticweb.dictionary.resticweb_variables import Config

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
        with LocalSession() as session:
            repository = session.query(Repository).filter_by(id=self.parameter_dictionary['repository']).first()
            if not repository:
                raise Exception("Invalid repository or repository has been deleted")
            repo_address = repository.address
            backup_objects = session.query(BackupObject).filter_by(backup_set_id=self.parameter_dictionary['backup_set'])
            if not backup_objects:
                raise Exception("Backup set has been deleted or the backup is empty")
            object_list = [bak_object.data for bak_object in backup_objects]
        repo_password = credential_manager.get_group_credentials(repository.credential_group_id).get('repo_password')
        process_object = self.job_class(address=repo_address, repo_password=repo_password, object_list=object_list, engine_location=Config.ENGINE_COMMAND)
        self.job_object = job_tools.JobObject(name=self.job_name, process=process_object)

    def construct_job_object_repository(self):
        process_object = self.job_class(address=self.parameter_dictionary['address'],
                                        repo_password=self.parameter_dictionary['repo_password'],
                                        field_dict=self.parameter_dictionary['field_dict'],
                                        engine_location=Config.ENGINE_COMMAND)
        self.job_object = job_tools.JobObject(name=self.job_name, process=process_object)
        self.job_object.success_callback = job_callbacks.repository_add_to_db

    def construct_job_object_restore(self):
        repo_password = credential_manager.get_group_credentials(self.parameter_dictionary['repository'].credential_group_id).get('repo_password')
        repo_address = self.parameter_dictionary['repository'].address
        process_object = self.job_class(repo_address=repo_address,
                                        repo_password=repo_password,
                                        destination_address=self.parameter_dictionary['destination_address'],
                                        engine_location=Config.ENGINE_COMMAND,
                                        object_list=self.parameter_dictionary.get('object_list'),
                                        snapshot_id=self.parameter_dictionary['snapshot_id'])
        self.job_object = job_tools.JobObject(name=self.job_name, process=process_object)

    def construct_job_object_forget(self):
        with LocalSession() as session:
            repository = session.query(Repository).filter_by(id=self.parameter_dictionary['repository']).first()
            if not repository:
                raise Exception("Invalid repository or repository has been deleted")
            repo_address = repository.address
        repo_password = credential_manager.get_group_credentials(repository.credential_group_id).get('repo_password')
        process_object = self.job_class(address=repo_address, repo_password=repo_password, engine_location=Config.ENGINE_COMMAND, snapshot_id=self.parameter_dictionary['snapshot_id'])
        self.job_object = job_tools.JobObject(name=self.job_name, process=process_object)

    def construct_job_object_check(self):
        with LocalSession() as session:
            repository = session.query(Repository).filter_by(id=self.parameter_dictionary['repository']).first()
            if not repository:
                raise Exception("Invalid repository or repository has been deleted")
        repo_password = credential_manager.get_group_credentials(repository.credential_group_id).get('repo_password')
        repo_address = repository.address
        process_object = self.job_class(repo_address=repo_address, repo_password=repo_password, engine_location=Config.ENGINE_COMMAND)
        self.job_object = job_tools.JobObject(name=self.job_name, process=process_object)

    def construct_job_object_prune(self):
        with LocalSession() as session:
            repository = session.query(Repository).filter_by(id=self.parameter_dictionary['repository']).first()
            if not repository:
                raise Exception("Invalid repository or repository has been deleted")
        repo_password = credential_manager.get_group_credentials(repository.credential_group_id).get('repo_password')
        repo_address = repository.address
        process_object = self.job_class(repo_address=repo_address, repo_password=repo_password, engine_location=Config.ENGINE_COMMAND)
        self.job_object = job_tools.JobObject(name=self.job_name, process=process_object)

    def construct_job_object_repository_sync(self):
        with LocalSession() as session:
            repository = session.query(Repository).filter_by(id=self.parameter_dictionary['repository']).first()
            if not repository:
                raise Exception("Invalid repository or repository has been deleted")
        process_object = self.job_class(repo_id=repository.id)
        self.job_object = job_tools.JobObject(name=self.job_name, process=process_object)
        
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