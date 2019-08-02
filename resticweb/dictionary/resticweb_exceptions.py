class DbCommitException(Exception):
    pass


class DbQueryException(Exception):
    pass


class DbGeneralException(Exception):
    pass


class CredentialsLockedException(Exception):
    pass


class BSNotSupportedException(Exception):
    pass


class UBInitFailure(Exception):
    pass


class JobQueueFullException(Exception):
    pass


class NoEngineAvailable(Exception):
    pass


class ResourceGeneralException(Exception):
    pass


class ResourceInUse(Exception):
    pass


class ResourceExists(Exception):
    pass


class ResourceNotFound(Exception):
    pass


class ResourceUnavailable(Exception):
    pass


class ResourceOffline(Exception):
    pass