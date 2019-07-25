from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, ValidationError, \
    SelectField, TextAreaField, HiddenField, BooleanField
from resticweb.tools.local_session import LocalSession
from resticweb.models.general import Repository, RepositoryType
from wtforms.validators import DataRequired


class AddRepositoryTypeForm(FlaskForm):
    name = StringField('Name')
    type = StringField('Type')
    description = TextAreaField('Description')
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            repository_type = session.query(RepositoryType).filter_by(name=name.data).first()
            if repository_type:
                raise ValidationError(f"Repository type with name {name.data} already exists. Please pick a different name.")



class UBCredentialField(StringField):
    pass


class EditRepositoryTypeForm(FlaskForm):
    repository_type_id = HiddenField('Id')
    name = StringField('Name')
    type = StringField('Type')
    description = TextAreaField('Description')
    submit = SubmitField('Submit')
    
    def validate_name(self, name):
        with LocalSession() as session:
            repository_type = session.query(RepositoryType).filter_by(name=name.data).first()
            if repository_type and repository_type.id != int(self.repository_type_id.data):
                raise ValidationError(f"Repository type with name {name.data} already exists. Please pick a different name.")


class AddRepositoryForm1(FlaskForm):
    repository_id = HiddenField('Id')
    address = StringField("Address")
    internal_name = StringField("Internal Name")
    repo_password = UBCredentialField("Repo Password")
    description = TextAreaField("Internal Description")
    cache_repo = BooleanField("Cache repository objects")
    submit = SubmitField("Submit")

    def validate_internal_name(self, internal_name):
            with LocalSession() as session:
                repository = session.query(Repository).filter_by(internal_name=internal_name.data).first()
                if repository and repository.id != int(self.repository_id.data):
                    raise ValidationError(f"Location with name {internal_name.data} already exists. Please pick a different name.")


class EditRepositoryForm1(FlaskForm):
    repository_id = HiddenField('Id')
    address = StringField("Address")
    internal_name = StringField("Internal Name")
    description = TextAreaField("Internal Description")
    cache_repo = BooleanField("Cache repository objects")
    submit = SubmitField("Submit")

    def validate_internal_name(self, internal_name):
            with LocalSession() as session:
                repository = session.query(Repository).filter_by(internal_name=internal_name.data).first()
                if repository and repository.id != int(self.repository_id.data):
                    raise ValidationError(f"Location with name {internal_name.data} already exists. Please pick a different name.")


def get_add_repository_form(repository_type):
    if repository_type == 1:
        return AddRepositoryForm1()
    else:
        raise Exception("Unsupported repository type")


def get_edit_repository_form(repository_type):
    if repository_type == 1:
        return EditRepositoryForm1()
    else:
        raise Exception("Unsupported repository type")
