from resticweb import db, bcrypt
from resticweb.models.general import CredentialGroup, CredentialStore, SysVars, RepositoryType
from resticweb.dictionary.resticweb_constants import System, Credential
from resticweb.blueprints.users.models import User
from sqlalchemy.exc import OperationalError
import logging
from resticweb.dictionary.resticweb_exceptions import UBInitFailure


def init_db():
    logger = logging.getLogger("mainLogger")
    try:
        db_initialized = SysVars.query.filter_by(
            var_name=System.DB_INITIALIZED_VAR_NAME).first()
    except OperationalError as e:
        raise UBInitFailure("init_db was called before the databases/tables "
                            f"were created. ---- {e}")
    if db_initialized is None:
        pass  # db not initialized so we can proceed with initialization
    elif db_initialized.var_data == "1":
        return  # we can safely return if the db has been initialized

    # initialize the storage for the credential database encryption key
    credential_key_group = CredentialGroup(
            id=0,
            service_name=Credential.CREDENTIAL_KEY_GROUP_NAME)
    credential_key = CredentialStore(
        group_id=0,
        credential_role=Credential.CREDENTIAL_KEY_ROLE_NAME,
        credential_data=""
    )
    db.session.add(credential_key_group)
    db.session.add(credential_key)

    # initialize the indicator whether or not credential database is encrypted
    cred_db_encrypted = SysVars(
        var_name=Credential.CREDENTIAL_DB_ENCRYPTED,
        var_data="0"
    )
    db.session.add(cred_db_encrypted)

    # add a default username and password for logging in
    user = User(
        username="admin",
        password=bcrypt.generate_password_hash("password").decode('utf-8')
    )
    db.session.add(user)

    # we'll try committing all those objects that we have just added
    try:
        db.session.commit()
    except OperationalError as e:
        logger.error(f"Failed to initialize the database: {e}")
        raise UBInitFailure

    # we can finally declare the database as initialized
    db_initialized = SysVars(
        var_name=System.DB_INITIALIZED_VAR_NAME,
        var_data="1"
    )
    db.session.add(db_initialized)

    # add default repository types
    repository_type_type = RepositoryType(
        id=1,
        name="Local Filesystem",
        type="local",
        internal_binding='local',
        description="Location type referencing a place in the filesystem on the same machine as the server")
    db.session.add(repository_type_type)

    repository_type_type = RepositoryType(
        id=2,
        name="Amazon S3",
        type="cloud",
        internal_binding='amazons3',
        description="Repository type referencing a place in an Amazon S3 bucket.")
    db.session.add(repository_type_type)

    repository_type_type = RepositoryType(
        id=3,
        name="RClone",
        type="cloud",
        internal_binding='rclone',
        description="Placeholder for RClone repository types. Feel free to create custom ones that correspond to your repo locations.")
    db.session.add(repository_type_type)

    db.session.commit()