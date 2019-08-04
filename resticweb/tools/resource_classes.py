from resticweb.dictionary.resticweb_exceptions import ResourceGeneralException, ResourceUnavailable, ResourceOffline
import logging
from resticweb.interfaces.repository_list import get_repository_status
'''
Resource objects will track the checkout status of each resource.
Each resource object will correspond either to an item on the SQL DB
or an arbitrary resource that might appear later
'''
class Resource():

    name = None
    type = None
    total = 0
    checked_out = 0
    available = 0
    availability_timeout = 0
    resource_holder_tokens = [] # [(holder, amount)]
    logger = logging.getLogger('debugLogger')    

    def __init__(self, total, availability_timeout=60, name=None, type=None):
        self.total = total
        self.available = total
        self.availability_timeout = availability_timeout
        self.name = name
        self.type = type

    def is_available(self, amount):
        return self.available >= amount

    def set_total(self, total):
        if total - self.checked_out < 0:
            raise ResourceGeneralException('Resource amount cannot be lower than the number currently checked out')
        self.total = total
        self.available = self.checked_out - total

    def get_availability_timeout(self):
        return self.availability_timeout

    # for a resource to be able to be checked out, it has to have
    # enough available resources and the resource object has to be
    # online
    def checkout(self, source, exclusive=False, amount=1):
        if exclusive:
            amount = self.total
        if not self.is_available(amount):
            raise ResourceUnavailable(f'Cannot reserve {amount} of resource {self.name} when only {self.available} is available.')
        if not self.is_online():
            raise ResourceOffline(f'Resource {self.name} is currently offline and cannot be checked out.')
        # at this point we should be able to reserve the resource
        self.available -= amount
        self.checked_out += amount
        resource_token = ResourceToken(self.type, self.name, amount, source)
        self.resource_holder_tokens.append(resource_token)
        return resource_token

    '''
    def DEL_checkin(self, source, exclusive=False, amount=1):
        if exclusive:
            amount = self.total
        try:
            self.resource_holders.remove((source, amount))
        except ValueError:
            raise ResourceGeneralException(f'{source} tried to check in a resource or resource amount that it has not checked out.')
        self.available += amount
        self.checked_out -= amount
    '''

    def checkin(self, token):
        try:
            self.resource_holder_tokens.remove(token)
        except ValueError:
            raise ResourceGeneralException(f'{token.source} tried to check in a resource or resource amount that it has not checked out.')
        self.available += token.amount
        self.checked_out -= token.amount

    def who_checked_out(self):
        return [(token.source, token.amount) for token in self.resource_holder_tokens]

    def is_online(self):
        return True


class BackupSetRes(Resource):

    pass


class RepositoryRes(Resource):
    
    def is_online(self):
        if get_repository_status(int(self.name)) == "Online":
            return True
        else:
            return False

class ResourceToken():

    def __init__(self, resource_type, resource_id, amount, source):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.amount = amount
        self.source = source