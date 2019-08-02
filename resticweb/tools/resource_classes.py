from resticweb.dictionary.resticweb_exceptions import ResourceGeneralException, ResourceUnavailable, ResourceOffline

'''
Resource objects will track the checkout status of each resource.
Each resource object will correspond either to an item on the SQL DB
or an arbitrary resource that might appear later
'''
class Resource():

    name = None
    total = 0
    checked_out = 0
    available = 0
    availability_timeout = 0
    resource_holders = [] # [(holder, amount)]

    def __init__(self, total, availability_timeout=60):
        self.total = total
        self.availability_timeout = availability_timeout

    def is_available(self, amount):
        return self.available >= amount

    def set_total(self, total):
        if total - self.checked_out < 0:
            raise ResourceGeneralException('Resource amount cannot be lower than the number currently checked out')
        self.total = total

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
        self.resource_holders.append((source, amount))

    def checkin(self, source, exclusive=False, amount=1):
        if exclusive:
            amount = self.total
        try:
            self.resource_holders.remove((source, amount))
        except ValueError:
            raise ResourceGeneralException(f'{source} tried to check in a resource or resource amount that it has not checked out.')
        self.available += amount
        self.checked_out -= amount

    def who_checked_out(self):
        return self.resource_holders        

    def is_online(self):
        return True


class BackupSetRes(Resource):

    pass


class RepositoryRes(Resource):

    pass