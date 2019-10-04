class JobStatus:
    JOB_STATUS_RUNNING = 10
    JOB_STATUS_QUEUED = 20
    JOB_STATUS_ACQUIRING_RESOURCES = 21
    JOB_STATUS_WAITING_RESOURCES = 22
    JOB_STATUS_PAUSED = 30
    JOB_STATUS_FINISHED = 40
    JOB_STATUS_CANCELLED = 50


class JobStatusMap:
    JOB_STATUS = {
        JobStatus.JOB_STATUS_RUNNING: 'Running',
        JobStatus.JOB_STATUS_QUEUED: 'Queued',
        JobStatus.JOB_STATUS_PAUSED: 'Paused',
        JobStatus.JOB_STATUS_FINISHED: 'Finished',
        JobStatus.JOB_STATUS_ACQUIRING_RESOURCES: 'Acquiring resources',
        JobStatus.JOB_STATUS_WAITING_RESOURCES: 'Waiting for one or more resources',
        JobStatus.JOB_STATUS_CANCELLED: 'Job cancelled'
    }


class JobStatusFinished:
    JOB_STATUS_SUCCESS = 10
    JOB_STATUS_WARNING = 20
    JOB_STATUS_ERROR = 30


class JobStatusFinishedMap:
    JOB_STATUS_FINISHED = {
        JobStatusFinished.JOB_STATUS_SUCCESS: 'Success',
        JobStatusFinished.JOB_STATUS_WARNING: 'Warning',
        JobStatusFinished.JOB_STATUS_ERROR: 'Error'
    }


class BackupSetTypes:
    BS_TYPE_FILESFOLDERS = 0
    BS_TYPE_FILESFOLDERS_DESC = "Files and Folders"


# might put these in the database later
class BackupSetList:
    BACKUP_SETS = {
        BackupSetTypes.BS_TYPE_FILESFOLDERS: BackupSetTypes.BS_TYPE_FILESFOLDERS_DESC
    }


class RepositoryTypeBindings:
    REPOSITORY_LOCAL = 'local'
    REPOSITORY_AMAZON_S3 = 'amazons3'
    REPOSITORY_RCLONE = 'rclone'
    binding_list = [REPOSITORY_LOCAL, REPOSITORY_AMAZON_S3, REPOSITORY_RCLONE]


class Credential:
    CREDENTIAL_ENVIRONMENT_VAR_NAME = "UB_CREDENTIAL_STORE_PASSWORD"
    CREDENTIAL_KEY_GROUP_NAME = "CREDENTIAL_PASSWORD"
    CREDENTIAL_KEY_ROLE_NAME = "KEY"
    CREDENTIAL_DB_ENCRYPTED = "CREDENTIAL_DB_ENCRYPTED"


class System:
    DB_INITIALIZED_VAR_NAME = "DB_INITIALIZED"
    DEFAULT_TIME_FORMAT = "%m-%d-%YT%H:%M:%S"
    # sometimes the process might report its' status as finished and
    # then the process will terminate, but the elif statements might
    # already be past the 'status' == 'success' for example and will
    # fall under the 'not alive' statement and it will think that the
    # process quit before it was able to report its status.
    # we can mitigate this by setting a timer to give the job plenty of time
    # to finish
    DEAD_PROCESS_TIMEOUT = 30 # in seconds


class ScheduleConstants:
    TIME_UNITS = [
        'minutes',
        'minute',
        'hours',
        'hour',
        'days',
        'day',
        'weeks',
        'week'#,
        #'monday',
        #'tuesday',
        #'wednesday',
        #'thursday',
        #'friday',
        #'saturday',
        #'sunday'
    ]


class MiscResticConstants:
    FILE_EXCLUSION_KEY = '-'
    FILE_INCLUSION_KEY = '+'

