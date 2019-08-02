from resticweb.dictionary.resticweb_exceptions import ResourceInUse, ResourceExists,\
    ResourceNotFound, ResourceGeneralException
from threading import RLock
import resticweb.interfaces.backup_sets as backup_sets_interface
import resticweb.interfaces.repository_list as repository_list_interface
import resticweb.tools.resource_classes as resource_classes

# for a job to be running in parallel, we want to make sure we do not
# have too many jobs accessing the same resource at one time (ex. Repository)
# as that might overload the resource or the resource might just not be available
# to be used at all while being used by another job. The resource manager
# should provide an easy way to manage the resources so that the job runner
# can properly wait for a job to be able to run instead of running it and then
# running into an error.

class ResourceManager():
    '''
    Resources format:
        "resource type": {
            "resource id": resource object
        } 
    '''
    resources = {}
    t_lock = RLock()

    # populate_resources takes in a list of resources:
    # list contains dict: {resource_type, resource_id, resource_object}
    def populate_resources(self, resources):
        for resource in resources:
            self.add_resource(resource['resource_type'], resource['resource_id'], resource['resource_object'])

    def add_resource(self, resource_type, resource_id, resource_object):
        with self.t_lock:
            if not self.resources[resource_type]:
                self.resources[resource_type] = dict()
            if not self.resources[resource_type].get(resource_id):
                self.resources[resource_type][resource_id] = resource_object
            else:
                raise ResourceExists('Cannot add the resource as there already exists one with the same id.')

    def get_resource(self, resource_type, resource_id):
        try:
            return self.resources[resource_type][resource_id]
        except ValueError:
            raise ResourceNotFound(f'Resource {resource_id} of type {resource_type} not found.')

    def update_resource_amount(self, resource_type, resource_id, new_amount=None):
        if new_amount:
            with self.t_lock:
                self.get_resource(resource_type, resource_id).set_total(new_amount)
    '''
    def update_resource_id(self, resource_type, resource_id, new_id=None):
        self._check_if_type_exists(resource_type)
        self._check_if_id_exists(resource_type, resource_id)
        if self.resources[resource_type].get(new_id):
            raise ResourceExists(f'Resource with id {new_id} already exists.')
        if new_id:
            with self.t_lock:
                self.resources[resource_type][new_id] = self.resources[resource_type].pop(resource_id)
                if self.how_many_checked_out(resource_type, resource_id) > 0:
                    self.checked_out_resources[resource_type][new_id] =  self.checked_out_resources[resource_type].pop(resource_id)
    '''

    def type_exists(self, resource_type):
        if self.resources.get(resource_type):
            return True
        return False
        
    def id_exists(self, resource_type, resource_id):
        if self.type_exists(resource_type) and self.resources[resource_type].get(resource_id):
            return True
        return False

    def remove_resource(self, resource_type, resource_id):
        if self.how_many_checked_out(resource_type, resource_id) > 0:
            raise ResourceInUse('Resource cannot be removed as it is currently in use.')
        try:
            self.resources[resource_type].pop(resource_id)
        except ValueError:
            pass

    def checkout(self, resource_type, resource_id, source, exclusive=False, amount=1):
        with self.t_lock:
            self.get_resource(resource_type, resource_id).checkout(source, exclusive, amount)

    def checkin(self, resource_type, resource_id, source, exclusive=False, amount=1):
        with self.t_lock:
            self.get_resource(resource_type, resource_id).checkin(source, exclusive, amount)

    def how_many_checked_out(self, resource_type, resource_id):
        return self.get_resource(resource_type, resource_id).checked_out

    def who_checked_out(self, resource_type, resource_id):
        self.get_resource(resource_type, resource_id).who_checked_out()

    def how_many_available(self, resource_type, resource_id):
        return self.get_resource(resource_type, resource_id).available

    def how_many_total(self, resource_type, resource_id):
        return self.get_resource(resource_type, resource_id).total


'''
An extension of the ResourceManager that integrates better with resticweb
We can use the resource type and id in order to grab the appropriate resource
and get its amount directly from the database. It also adds/removes the
resources as they are checked in/out so that all of the objects are not kept
at all times consuming memory
'''
class RWResourceManager(ResourceManager):

    def checkout(self, resource_type, resource_id, source, exclusive=False, amount=1):
        if resource_type == 'repository':
            repository_info = repository_list_interface.get_info(resource_id)
            if self.id_exists(resource_type, repository_info['id']):
                super(resource_type, resource_id, source, exclusive, amount)
            else:
                self.add_resource(resource_type, resource_id, resource_classes.RepositoryRes(amount, repository_info['timeout']))
                super(resource_type, resource_id, source, exclusive, amount)
        elif resource_type == 'backup_set':
            backup_set_info = backup_sets_interface.get_backup_set_info(resource_id, False)
            if self.id_exists(resource_type, backup_set_info['id']):
                super(resource_type, resource_id, source, exclusive, amount)
            else:
                self.add_resource(resource_type, resource_id, resource_classes.RepositoryRes(amount, backup_set_info['timeout']))
                super(resource_type, resource_id, source, exclusive, amount)

    def checkin(self, resource_type, resource_id, source, exclusive=False, amount=1):
        super(resource_type, resource_id, source, exclusive, amount)
        if self.how_many_checked_out(resource_type, resource_id) < 1:
            self.remove_resource(resource_type, resource_id)