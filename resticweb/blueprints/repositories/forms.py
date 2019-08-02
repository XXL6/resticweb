from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, ValidationError, \
    SelectField, TextAreaField, HiddenField, BooleanField
from resticweb.tools.local_session import LocalSession
from resticweb.models.general import Repository, RepositoryType
from wtforms.validators import DataRequired
from resticweb.dictionary.resticweb_constants import RepositoryTypeBindings


class AddRepositoryTypeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    type = StringField('Type', validators=[DataRequired()])
    description = TextAreaField('Description')
    internal_binding = SelectField('Internal Binding')
    submit = SubmitField('Submit')

    def __init__(self):
        super().__init__()
        bindings = []
        for item in RepositoryTypeBindings.binding_list:
            bindings.append((item, item))
        self.internal_binding.choices = bindings
    
    def validate_name(self, name):
        with LocalSession() as session:
            repository_type = session.query(RepositoryType).filter_by(name=name.data).first()
            if repository_type:
                raise ValidationError(f"Repository type with name {name.data} already exists. Please pick a different name.")



class UBCredentialField(StringField):
    pass


class EditRepositoryTypeForm(FlaskForm):
    repository_type_id = HiddenField('Id')
    name = StringField('Name', validators=[DataRequired()])
    type = StringField('Type', validators=[DataRequired()])
    description = TextAreaField('Description')
    internal_binding = SelectField('Internal Binding')
    submit = SubmitField('Submit')

    def __init__(self):
        super().__init__()
        bindings = []
        for item in RepositoryTypeBindings.binding_list:
            bindings.append((item, item))
        self.internal_binding.choices = bindings
    
    def validate_name(self, name):
        with LocalSession() as session:
            repository_type = session.query(RepositoryType).filter_by(name=name.data).first()
            if repository_type and repository_type.id != int(self.repository_type_id.data):
                raise ValidationError(f"Repository type with name {name.data} already exists. Please pick a different name.")


class AddRepositoryFormBase(FlaskForm):
    repository_id = HiddenField('Id')
    name = StringField("Name", validators=[DataRequired()])
    repo_password = UBCredentialField("Repo Password", validators=[DataRequired()])
    description = TextAreaField("Description")
    cache_repo = BooleanField("Cache repository objects")
    concurrent_uses = IntegerField("Concurrent job uses")
    timeout = IntegerField("Timeout (minutes)")
    submit = SubmitField("Submit")

    def validate_name(self, name):
            with LocalSession() as session:
                repository = session.query(Repository).filter_by(name=name.data).first()
                if repository and repository.id != int(self.repository_id.data):
                    raise ValidationError(f"Location with name {name.data} already exists. Please pick a different name.")


class EditRepositoryFormBase(FlaskForm):
    repository_id = HiddenField('Id')
    name = StringField("Name", validators=[DataRequired()])
    description = TextAreaField("Description")
    cache_repo = BooleanField("Cache repository objects")
    concurrent_uses = IntegerField("Concurrent job uses")
    timeout = IntegerField("Timeout (minutes)")
    submit = SubmitField("Submit")

    def validate_name(self, name):
            with LocalSession() as session:
                repository = session.query(Repository).filter_by(name=name.data).first()
                if repository and repository.id != int(self.repository_id.data):
                    raise ValidationError(f"Location with name {name.data} already exists. Please pick a different name.")


class AddRepositoryForm1(AddRepositoryFormBase):
    address = StringField("Address", validators=[DataRequired()])


class EditRepositoryForm1(EditRepositoryFormBase):
    address = StringField("Address", validators=[DataRequired()])

    def set_current_data(self, current_data):
        self.address.data = current_data['address']

class AddRepositoryForm2(AddRepositoryFormBase):
    bucket_name = StringField("Bucket Name", validators=[DataRequired()])
    AWS_ACCESS_KEY_ID = UBCredentialField("AWS Access Key Id", validators=[DataRequired()])
    AWS_SECRET_ACCESS_KEY = UBCredentialField("AWS Secret Access Key", validators=[DataRequired()])


class EditRepositoryForm2(EditRepositoryFormBase):
    bucket_name = StringField("Bucket Name", validators=[DataRequired()])

    def set_current_data(self, current_data):
        self.bucket_name.data = current_data['bucket_name']


def get_add_repository_form(repository_type):
    if repository_type == 'local':
        return AddRepositoryForm1()
    elif repository_type == 'amazons3':
        return AddRepositoryForm2()
    else:
        raise Exception("Unsupported repository type")


def get_edit_repository_form(repository_type):
    if repository_type == 'local':
        return EditRepositoryForm1()
    elif repository_type == 'amazons3':
        return EditRepositoryForm2()
    else:
        raise Exception("Unsupported repository type")
