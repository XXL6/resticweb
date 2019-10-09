from .repository import Repository, RepositorySync
from .backup import Backup
from .restore import Restore
from .test import Test
from .check import Check
from .forget import Forget
from .prune import Prune
from .forget_policy import ForgetPolicy

# maps the lowercase name of a class to the actual class
def get_class_from_name(class_name):
    if class_name == 'repository':
        return Repository
    elif class_name == 'backup':
        return Backup
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
    elif class_name == 'forget_policy':
        return ForgetPolicy
    else:
        return None

# function used to present job options to the front-end
def get_available_classes():
    classes = [('backup', 'Backup'), 
            ('repository', 'Repository Create'),
            ('restore', 'Restore'), 
            ('check', 'Check'),
            ('prune', 'Prune'),
            ('forget_policy', 'Forget')]
    return classes