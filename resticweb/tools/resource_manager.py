from resticweb.dictionary.resticweb_exceptions import ResourceInUse, ResourceExists,\
    ResourceNotFound, ResourceGeneralException
from threading import RLock
import resticweb.interfaces.backup_sets as backup_sets_interface
import resticweb.interfaces.repository_list as repository_list_interface
import resticweb.tools.resource_classes as resource_classes
import logging

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
    logger = logging.getLogger('debugLogger')
    # populate_resources takes in a list of resources:
    # list contains dict: {resource_type, resource_id, resource_object}
    def populate_resources(self, resources):
        for resource in resources:
            self.add_resource(resource['resource_type'], resource['resource_id'], resource['resource_object'])

    def add_resource(self, resource_type, resource_id, resource_object):
        with self.t_lock:
            if not self.resources.get(resource_type):
                self.resources[resource_type] = dict()
            if not self.resources[resource_type].get(resource_id):
                self.resources[resource_type][resource_id] = resource_object
            else:
                raise ResourceExists('Cannot add the resource as there already exists one with the same id.')

    def get_resource(self, resource_type, resource_id):
        try:
            return self.resources[resource_type][resource_id]
        except KeyError:
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
        if self.type_exists(resource_type):
            if self.resources[resource_type].get(resource_id):
                return True
        return False

    def remove_resource(self, resource_type, resource_id):
        if self.how_many_checked_out(resource_type, resource_id) > 0:
            raise ResourceInUse('Resource cannot be removed as it is currently in use.')
        try:
            self.resources[resource_type].pop(resource_id)
        except KeyError:
            pass

    def get_availability_timeout(self, resource_type, resource_id):
        return self.get_resource(resource_type, resource_id).get_availability_timeout()

    def checkout(self, resource_type, resource_id, source, exclusive=False, amount=1):
        with self.t_lock:
            return self.get_resource(resource_type, resource_id).checkout(source, exclusive, amount)

    def checkin(self, resource_token):
        with self.t_lock:
            self.get_resource(resource_token.resource_type, resource_token.resource_id).checkin(resource_token)

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

    # same as regular checkout, but we can also try getting a value from one of the
    # predefined resticweb tables.
    def checkout(self, resource_type, resource_id, source, exclusive=False, amount=1):
        if self.id_exists(resource_type, resource_id):
            return super().checkout(resource_type, resource_id, source, exclusive, amount)
        else:
            resource_object = self.get_resource_from_table(resource_type, resource_id)
            if resource_object:
                self.add_resource(resource_type, resource_id, resource_object)
            try:
                return super().checkout(resource_type, resource_id, source, exclusive, amount)
            except Exception as e:
                self.remove_resource(resource_type, resource_id)
                raise e

    '''
    def DEL_checkin(self, resource_type, resource_id, source, exclusive=False, amount=1):
        super(resource_type, resource_id, source, exclusive, amount)
        if self.how_many_checked_out(resource_type, resource_id) < 1:
            self.remove_resource(resource_type, resource_id)
    '''
    # If upon checking in a token there is nothing else using a resource,
    # we can remove it from the resource list so it might use less memory
    def checkin(self, resource_token):
        super().checkin(resource_token)
        if self.how_many_checked_out(resource_token.resource_type, resource_token.resource_id) < 1:
            self.remove_resource(resource_token.resource_type, resource_token.resource_id)

    # this method might sometimes get called when the resource is not added to the resource
    # list but we want to find out how much we might need to wait on it in case it's unavailable
    def get_availability_timeout(self, resource_type, resource_id):
        try:
            return super().get_availability_timeout(resource_type, resource_id)
        except ResourceNotFound as e:
            resource_object = self.get_resource_from_table(resource_type, resource_id)
            if resource_object:
                return resource_object.get_availability_timeout()
            else:
                raise e
    
    def get_resource_from_table(self, resource_type, resource_id):
        resource_object = None
        if resource_type == 'repository':
            repository_info = repository_list_interface.get_info(resource_id, None, True, False)
            if repository_info:
                resource_object = resource_classes.RepositoryRes(repository_info['concurrent_uses'], repository_info['timeout'], name=resource_id, type=resource_type)
        elif resource_type == 'backup_set':
            backup_set_info = backup_sets_interface.get_backup_set_info(resource_id, False)
            if backup_set_info:
                resource_object = resource_classes.BackupSetRes(backup_set_info['concurrent_uses'], backup_set_info['timeout'], name=resource_id, type=resource_type)
        return resource_object