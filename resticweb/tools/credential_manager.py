from os import environ
from resticweb.models.general import CredentialStore, SysVars,\
    CredentialGroup
from resticweb.dictionary.resticweb_constants import Credential
from resticweb.dictionary.resticweb_exceptions import CredentialsLockedException
from sqlalchemy import exc, create_engine
from sqlalchemy.orm import sessionmaker
import resticweb.tools.crypt_tools as crypt_tools
import logging
import bcrypt
from sqlalchemy.exc import OperationalError
from resticweb.tools.local_session import LocalSession
import traceback


class CredentialManager():

    def __init__(self):
        self.logger = logging.getLogger('mainLogger')
        # engine = create_engine('sqlite:///resticweb/ub_system.db')
        # Session = sessionmaker(bind=engine)
        # self.session = Session()
        # if the database is encrypted we want to say that it's
        # locked as well on initialization, but if the database
        # is not encrypted, then the credentials would not be locked
        # if there's an attribute error or an operational error
        # that usually means that the database has not yet been initialized
        # and we can then deduce that the database would not de encrypted
        # either
        try:
            self._credentials_locked = self.credentials_encrypted()
        except OperationalError:
            # self.logger.warning(traceback.format_exc())
            self.logger.error("Operational Error still")
            self._credentials_locked = False
        except AttributeError:
            # self.logger.warning(traceback.format_exc())
            self.logger.warning("Attribute error thingy")
            self._credentials_locked = False
        # crypt key kept in memory
        self.crypt_key = ""

    def get_local_session(self):
        engine = create_engine('sqlite:///resticweb/general.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        return session

    def assign_session(self, session):
        self.session = session

    def get_credential(self, group_id, credential_role):
        if self.credentials_encrypted() and self.credentials_locked():
            self.logger.error(f"Could not get credential data for "
                              f"role={credential_role} as "
                              "credential store is encrypted and locked")
            raise CredentialsLockedException
        session = self.get_local_session()
        credential = session.query(CredentialStore).filter_by(
                                            credential_role=credential_role,
                                            group_id=group_id).first()
        credential_data = credential.credential_data
        
        if credential:
            if self.credentials_encrypted():
                decryption_key = self.get_crypt_key()
                if decryption_key is None:
                    self.logger.error(f"Credential database marked as "
                                      "unlocked but no key provided")
                    raise Exception("No password specified for credential store")
                credential_data = crypt_tools.decrypt_string(
                    credential_data, decryption_key)
            return credential_data
        else:
            return ""

    def set_credential(self, group_id, credential_role, credential_data):
        if self.credentials_encrypted() and self.credentials_locked():
            self.logger.error(f"Could not set credential data for "
                              f"role={credential_role} as "
                              "credential store is encrypted and locked")
            raise CredentialsLockedException
        with LocalSession() as session:
            credential = session.query(CredentialStore).filter_by(
                                                credential_role=credential_role,
                                                group_id=group_id).first()
            if self.credentials_encrypted():
                encryption_key = self.get_crypt_key()
                if encryption_key is None:
                    self.logger.error(f"Credential database marked as "
                                    "unlocked but no key provided")
                    
                    raise Exception("No password specified for credential store")
                credential.credential_data = (crypt_tools.encrypt_string(
                    credential_data,
                    encryption_key)
                )
            else:
                credential.credential_data = credential_data
            session.commit()

    # returns a dictionary of credentials belonging to a certain group
    # format: {credential_role: credential_data}
    def get_group_credentials(self, group_id):
        if self.credentials_encrypted() and self.credentials_locked():
            self.logger.error(f"Could not get credentials for group="
                              f"{group_id} as credential store is "
                              "encrypted and locked")
            raise CredentialsLockedException
        with LocalSession() as session:
            credentials = session.query(CredentialStore).filter_by(
                group_id=group_id)
            return_credentials = {}
            if self.credentials_encrypted():
                decryption_key = self.get_crypt_key()
                if decryption_key is None:
                    self.logger.error(f"Credential database marked as "
                                    "unlocked but no key provided")
                    raise Exception("No password specified for credential store")
                for credential in credentials:
                    return_credentials[credential.credential_role] = crypt_tools.decrypt_string(
                        credential.credential_data, decryption_key)
            else:
                for credential in credentials:
                    return_credentials[credential.credential_role] = credential.credential_data
            return return_credentials

    def get_all_credential_groups(self):
        if self.credentials_encrypted() and self.credentials_locked():
            self.logger.error("Could not retrieve credentials while "
                              "the credential database is locked.")
            return []
        group_list = []
        with LocalSession() as session:
            credential_groups = session.query(CredentialGroup).filter(CredentialGroup.id > 0).order_by(
                CredentialGroup.id.asc())
            for group in credential_groups:
                temp_group = dict(
                    description=group.description,
                    service_name=group.service_name,
                    service_id=group.service_id,
                    group_id=group.id
                )
                group_list.append(temp_group)
            return group_list

    def credentials_encrypted(self):
        with LocalSession() as session:
            encrypted = session.query(SysVars).filter_by(
                var_name=Credential.CREDENTIAL_DB_ENCRYPTED).first()
            if encrypted:
                return encrypted.var_data == '1'
            else:
                return False

    def credentials_locked(self):
#        locked = self.session2.query(SysVarsMemory).filter_by(
#            var_name="CREDENTIAL_DATABASE_ENCRYPTED").first()
#        return locked.var_data == '1'
        return self._credentials_locked

    def set_credentials_encrypted(self, set_encrypted):
        with LocalSession() as session:
            encrypted = session.query(SysVars).filter_by(
                var_name=Credential.CREDENTIAL_DB_ENCRYPTED).first()
            encrypted.var_data = '1' if set_encrypted else '0'
            session.commit()

    def set_credentials_locked(self, set_locked):
 #       locked = self.session2.query(SysVarsMemory).filter_by(
 #           var_name="CREDENTIAL_DATABASE_ENCRYPTED").first()
 #       locked.var_data = '1' if set_locked else '0'
 #       self.session.commit()
        self._credentials_locked = set_locked

    def encrypt_credentials(self, encryption_key):
        if self.credentials_encrypted() or self.credentials_locked():
            self.logger.error("Credential database encryption was attempted, "
                              "however, the database is already encrypted "
                              "or locked")
            raise CredentialsLockedException
        self.set_crypt_key(encryption_key)
        encryption_key = self.get_crypt_key()
        with LocalSession() as session:
            try:
                # we do not encrypt group_id of 0 as that's the built-in group
                # to check the validity of encryption password
                credential_list = session.query(CredentialStore).filter(
                    CredentialStore.group_id > 0)
            except exc.SQLAlchemyError as e:
                self.logger.error(f"Failure to query credential database. {e}")
                raise
            for instance in credential_list:
                try:
                    encrypted_credential = crypt_tools.encrypt_string(
                        instance.credential_data, encryption_key)
                    instance.credential_data = encrypted_credential
                except Exception as e:
                    self.logger.error("Failed to encrypt credential database.")
                    self.logger.error(e)
                    raise Exception("Failed to encrypt credential database.")
            try:
                session.commit()
            except Exception as e:
                self.logger.error(
                    f"Failure to commit encrypted credential changes. {e}")
                raise
            self.store_crypt_key(encryption_key)
            # once all the checks complete we can conclude that the database
            # is now encrypted
            self.set_credentials_encrypted(True)

    # using the saved crypto key we decrypt all the credential_data
    # objects permanently and clear the old key from memory and
    # the database
    def decrypt_credentials(self):
        if self.credentials_locked():
            self.logger.error("Cannot decrypt credentials as the database "
                              "is locked.")
            raise CredentialsLockedException
        decryption_key = self.get_crypt_key()
        with LocalSession() as session:
            try:
                # we do not decrypt group_id of 0 as that's the
                # built-in group to check the validity
                # of encryption password
                credential_list = (session.query(CredentialStore).
                                filter(CredentialStore.group_id > 0))
            except exc.InvalidRequestError as e:
                self.logger.error(f"Failure to query credential database.")
                
                raise e
            except exc.SQLAlchemyError as e:
                self.logger.error(f"General DB error.")
                
                raise e
            for instance in credential_list:
                decrypted_credential = crypt_tools.decrypt_string(
                    instance.credential_data, decryption_key)
                instance.credential_data = decrypted_credential
            try:
                session.commit()
            except exc.InvalidRequestError as e:
                self.logger.error(
                    f"Failure to commit decrypted credential changes.")
                
                raise e
            except exc.SQLAlchemyError as e:
                self.logger.error(f"General DB error.")
                
                raise e
            
            self.set_crypt_key("")
            self.store_crypt_key("")
            # once all the checks complete we can conclude that the database
            # is now decrypted
            self.set_credentials_encrypted(False)

    # Basically if the encryption/decryption key is not currently set
    # the database is considered to be locked as the credential data
    # can no longer be decrypted on the fly
    def lock_credentials(self):
        # try:
        #    environ.unsetenv(Credential.CREDENTIAL_ENVIRONMENT_VAR_NAME)
        # except Exception as e:
        #    self.logger.error(f'Failed to lock credentials.')
        #    raise e
        self.set_crypt_key("")
        self.set_credentials_locked(True)

    def unlock_credentials(self, key):
        with LocalSession() as session:
            try:
                hashed_key = session.query(CredentialStore).filter_by(
                    group_id=0).first().credential_data
            except Exception as e:
                self.logger.error(f"Failure to query credential database "
                                "while unlocking credentials.")
                raise e
            if not bcrypt.checkpw(key.encode('utf-8'), hashed_key):
                self.logger.error(f"Wrong password provided for "
                                "credential unlocking")
                raise
            
            self.set_crypt_key(key)
            self.set_credentials_locked(False)

    def get_crypt_key(self):
        # return environ.get(Credential.CREDENTIAL_ENVIRONMENT_VAR_NAME)
        # crypt_key = self.session2.query(SysVarsMemory).filter_by(
        # var_name=Credential.CREDENTIAL_ENVIRONMENT_VAR_NAME).first()
        # return crypt_key
        return self.crypt_key

    # method used to store the user's cryptographic key for later use
    # can be changed if environmental variables are not wanted
    def set_crypt_key(self, key):
        # environ[Credential.CREDENTIAL_ENVIRONMENT_VAR_NAME] = key
        # crypt_key = self.session2.query(SysVarsMemory).filter_by(
        #    var_name=Credential.CREDENTIAL_ENVIRONMENT_VAR_NAME).first()
        # crypt_key.var_data = key
        # self.session.commit()
        # self.crypt_key = bcrypt.hashpw(str.encode(key), self.test_salt)
        self.crypt_key = key

    # stores and encrypts they key in the database using bcrypt
    # this way we can see whether the user input the right key
    # to unlock the database without having to store the key itself
    def store_crypt_key(self, key):
        with LocalSession() as session:
            try:
                credential = session.query(CredentialStore).filter_by(
                        credential_role=Credential.CREDENTIAL_KEY_ROLE_NAME,
                        group_id=0).first()
            except exc.InvalidRequestError as e:
                self.logger.error(f"Failure to query credential database "
                                "while storing cryptographic key.")
                raise e
            except exc.SQLAlchemyError as e:
                self.logger.error("General DB error.")
                raise e
            try:
                credential_group = (session.query(CredentialGroup).
                                    filter_by(id=0).first())
            except exc.InvalidRequestError as e:
                self.logger.error(f"Failure to query credential database "
                                "while storing cryptographic key.")
                raise e
            except exc.SQLAlchemyError as e:
                self.logger.error("General DB error.")
                raise e
            if credential_group and credential_group.service_name != \
                    Credential.CREDENTIAL_KEY_GROUP_NAME:
                self.logger.error(f"Wrong item in id=0 location of the "
                                "credential group table.")
                raise
            elif not credential_group:
                new_credential_group = CredentialGroup(
                    id=0,
                    description=Credential.CREDENTIAL_KEY_GROUP_NAME,
                    service_name=Credential.CREDENTIAL_KEY_GROUP_NAME)
                try:
                    session.add(new_credential_group)
                except exc.InvalidRequestError as e:
                    self.logger.error(f"Failure to add new credential group "
                                    "to the database.")
                    raise e
                except exc.SQLAlchemyError as e:
                    self.logger.error("General DB error.")
                    raise e
            if not credential:
                if key != "":
                    new_credential = CredentialStore(
                        group_id=0,
                        credential_role=Credential.CREDENTIAL_KEY_ROLE_NAME,
                        credential_data=bcrypt.hashpw(key.encode('utf-8'), bcrypt.gensalt()))
                else:
                    new_credential = CredentialStore(
                        group_id=0,
                        credential_role=Credential.CREDENTIAL_KEY_ROLE_NAME,
                        credential_data="")
                try:
                    session.add(new_credential)
                except exc.InvalidRequestError as e:
                    self.logger.error(f"Failure to add the credential "
                                    "password hash to the credential "
                                    "database.")
                    raise e
                except exc.SQLAlchemyError as e:
                    self.logger.error("General DB error.")
                    raise e
            else:
                if key != "":
                    credential.credential_data = bcrypt.hashpw(key.encode('utf-8'), bcrypt.gensalt())
                else:
                    credential.credential_data = ""
            session.commit()
            

    # removes all credential keys and groups
    # essentially has to be done if user encrypts
    # their database and forgets their password
    def reset_database(self):
        with LocalSession() as session:
            try:
                credentials_deleted = self.session.query(CredentialStore).filter(
                    CredentialStore.group_id > 0).\
                    delete(synchronize_session=False)
                session.commit()
            except exc.InvalidRequestError as e:
                self.logger.error(f"Failed to delete CredentialStore entries.")
                raise e
            except exc.SQLAlchemyError as e:
                self.logger.error("General DB error.")
                raise e
            try:
                credential_groups_deleted = (self.session.query(CredentialGroup).
                                            filter(CredentialGroup.id > 0).
                                            delete(synchronize_session=False))
                session.commit()
            except exc.InvalidRequestError as e:
                self.logger.error(f"Failed to reset CredentialGroup database.")
                raise e
            except exc.SQLAlchemyError as e:
                self.logger.error("General DB error.")
                raise e
            self.logger.info(f"[{credentials_deleted}] credentials deleted "
                            f" and [{credential_groups_deleted}] credential "
                            "groups deleted")
            
            self.set_credentials_encrypted(False)
            self.set_credentials_locked(False)
            self.set_crypt_key("")
            self.store_crypt_key("")

    # add a singular credential into the database
    # looks for a credential group with the specified
    # service name and assigns that group to the newly
    # added credential.
    # if it can't find the group with the specified
    # service name, it adds the group and then uses the newly
    # created group's id to create the credential
    def add_credential(self, service_name, service_id, credential_role, credential_data):
        with LocalSession() as session:
            if self.credentials_locked():
                self.logger.error(f"Unable to add [{credential_role}] "
                                f"for [{service_name}] as the credential "
                                "database is locked")
                raise CredentialsLockedException
            
            try:
                credential_group = (session.query(CredentialGroup).
                                    filter_by(service_name=service_name, service_id=service_id).first())
            except exc.InvalidRequestError as e:
                self.logger.error("Failed to query credential group database "
                                "while adding new credential.")
                raise e
            except exc.SQLAlchemyError as e:
                self.logger.error("General DB error.")
                raise e
            if credential_group:
                group_id = credential_group.id
            else:
                credential_group = CredentialGroup(service_name=service_name, service_id=service_id)
                session.add(credential_group)
                session.commit()
                group_id = credential_group.id
            new_credential = CredentialStore(
                credential_role=credential_role,
                credential_data=credential_data,
                group_id=group_id)
            if self.credentials_encrypted():
                new_credential.credential_data = crypt_tools.encrypt_string(
                    new_credential.credential_data,
                    self.get_crypt_key()
                )
            session.add(new_credential)
            session.commit()
            
            return group_id

    # credential_dict format: {credential_role: credential_data}
    # may have multiple tuples
    def add_credentials_from_dict(self, service_name, service_id, credential_dict):
        group_id = -1
        for key, value in credential_dict.items():
            group_id = self.add_credential(service_name, service_id, key, value)
        return group_id

    # Removes all credentials belonging to a certain group including
    # the group itself
    def remove_credentials(self, group_id):
        with LocalSession() as session:
            credentials_deleted = session.query(CredentialStore).filter_by(
                group_id=group_id).delete(synchronize_session=False)
            credential_group = session.query(CredentialGroup).filter_by(
                id=group_id).delete(synchronize_session=False)
            session.commit()
            
            if credentials_deleted > 0:
                self.logger.info(f"{credentials_deleted} credentials "
                                f"with group id of {group_id} have been deleted.")
            else:
                self.logger.warning(f"No credentials have been deleted for "
                                    f"group id of {group_id}")
            if credential_group > 0:
                self.logger.info(f"Credential group with id {group_id} "
                                "has been deleted.")
            else:
                self.logger.warning(f"No credential groups with id {group_id} "
                                    "have been deleted.")

    # sets a description to a credential group
    def set_group_description(self, group_id, description):
        with LocalSession() as session:
            credential_group = session.query(CredentialGroup).filter_by(
                id=group_id
            ).first()
            if not credential_group:
                self.logger.error(f"Unable to set description to "
                                f"group {group_id}")
                raise Exception
            credential_group.description = description
            session.commit()
            

    def get_group_description(self, group_id):
        with LocalSession() as session:
            credential_group = session.query(CredentialGroup).filter_by(
                id=group_id
            ).first()
            
            if not credential_group:
                self.logger.warning(f"Could not get group description for "
                                    f"group {group_id}.")
                return ""
            return credential_group.description

    def set_service_id(self, group_id, service_id):
        with LocalSession() as session:
            credential_group = session.query(CredentialGroup).filter_by(
                id=group_id
            ).first()
            if not credential_group:
                self.logger.error(f"Unable to set description to "
                                f"group {group_id}")
                raise Exception
            credential_group.service_id = service_id
            session.commit()
            
