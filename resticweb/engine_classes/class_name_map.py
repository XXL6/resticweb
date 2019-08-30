from .repository import Repository, RepositorySync
from .backup import Backup
from .restore import Restore
from .test import Test
from .check import Check
from .forget import Forget
from .prune import Prune

# maps the lowercase name of a class to the actual class
def get_class_from_name(class_name):
    if class_name == 'repository':
        return Repository
    elif class_name == 'backup':
        return Backup
    elif class_name == 'test':
        return Test
    elif class_name == 'restore':
        return Restore
    elif class_name == 'check':
        return Check
    elif class_name == 'forget':
        return Forget
    elif class_name == 'prune':
        return Prune
    elif class_name == 'repository_sync':
        return RepositorySync
    else:
        return None

# function used to present job options to the front-end
def get_available_classes():
    classes = [('backup', 'Backup'), 
            ('repository', 'Repository Create'), 
            ('test', 'Test'), 
            ('restore', 'Restore'), 
            ('check', 'Check'),
            ('prune', 'Prune')]
    return classes