from resticweb.dictionary.resticweb_constants import BackupSetTypes
from wtforms import StringField, SubmitField, TextField, SelectField,\
    TextAreaField, IntegerField, PasswordField, HiddenField, ValidationError
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm
from resticweb.tools.local_session import LocalSession
from resticweb.models.general import BackupSet, SavedJobs


class BSForm0(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    file_data = HiddenField('Data')
    concurrent_uses = IntegerField("Concurrent job uses", default=2)
    timeout = IntegerField("Timeout (minutes)", default=60)
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            backup_set = session.query(BackupSet).filter_by(name=name.data).first()
            if backup_set:
                raise ValidationError(f"Backup set with name {name.data} already exists. Please pick a different name.")


class BSForm0Edit(FlaskForm):
    backup_set_id = HiddenField('Id')
    name = StringField('Name', validators=[DataRequired()])
    file_data = HiddenField('Data')
    source = StringField('Source')
    concurrent_uses = IntegerField("Concurrent job uses")
    timeout = IntegerField("Timeout (minutes)")
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            backup_set = session.query(BackupSet).filter_by(name=name.data).first()
            if backup_set and backup_set.id != int(self.backup_set_id.data):
                raise ValidationError(f"Backup set with name {name.data} already exists. Please pick a different name.")


class AddBackupJobForm(FlaskForm):
    name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    backup_set = SelectField('Backup Set', coerce=int)
    repository = SelectField('Repository', coerce=int)
    additional_params = StringField('Additional Parameters')
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=name.data).first()
            if saved_job:
                raise ValidationError(f"Backup job with name {name.data} already exists. Please pick a different name.")


class EditBackupJobForm(FlaskForm):
    saved_job_id = HiddenField('Id')
    name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    backup_set = SelectField('Backup Set', coerce=int)
    repository = SelectField('Repository', coerce=int)
    additional_params = StringField('Additional Parameters')
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=name.data).first()
            if saved_job and saved_job.id != int(self.saved_job_id.data):
                raise ValidationError(f"Backup set with name {name.data} already exists. Please pick a different name.")

class RWCredentialField(StringField):
    pass


def get_backup_set_form(id):
    if id == 0:
        return BSForm0()


def get_backup_set_edit_form(type):
    if type == BackupSetTypes.BS_TYPE_FILESFOLDERS:
        return BSForm0Edit()
