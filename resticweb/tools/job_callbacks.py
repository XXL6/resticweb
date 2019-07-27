import resticweb.interfaces.repository_list as repository_interface
from resticweb.misc.credential_manager import credential_manager
from resticweb.tools.job_build import JobBuilder
import json

# adds the newly created repository information into the database
# also creates a credential record for this particular repository
def repository_add_to_db(job):
    data_dict = {}
    for key, value in job.process.field_dict.items():
        if ((key != 'name')
           and (key != 'description') 
           and (key != 'location')
           and (key != 'repository_id')):
            data_dict[key] = value
    global_credentials = job.process.repository_interface.global_credentials
    global_credentials['repo_password'] = global_credentials.pop('RESTIC_PASSWORD')
    credential_group_id = credential_manager.add_credentials_from_dict(
        'repository', 
        job.process.field_dict['name'],
        global_credentials)
    repo_id = repository_interface.add_repository(
        dict(
            name=job.process.field_dict['name'],
            description=job.process.field_dict['description'],
            repo_id=job.process.data.get('repo_id'),
            address=job.process.field_dict['address'],
            data=job.process.field_dict.get('data'),
            cache_repo=job.process.field_dict.get('cache_repo'),
            repository_type_id=job.process.field_dict['repository_type_id'],
            credential_group_id=credential_group_id
        )
    )
    # once the repository has been added successfully, we can sync the objects
    # if the 'cache_repo' was selected
    if job.process.field_dict.get('cache_repo'):
        job_builder = JobBuilder(job_name="Repository sync", job_class="repository_sync", parameters=dict(repository=repo_id))
        job_builder.run_job()

def test_backup_callback(job):
    for key, value in job.process.data['result'].items():
        print(f'{key} --- {value}')


