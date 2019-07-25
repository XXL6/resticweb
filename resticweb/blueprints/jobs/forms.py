from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, ValidationError, \
    SelectField, TextAreaField, HiddenField
from wtforms.validators import DataRequired
from resticweb.tools.local_session import LocalSession
from resticweb.models.general import SavedJobs


class AddJobForm(FlaskForm):
    ub_name = StringField('Job Name', validators=[DataRequired()])
    ub_description = TextAreaField('Description')
    submit = SubmitField('Submit')


class AddCheckJobForm(FlaskForm):
    saved_job_id = HiddenField('Id')
    internal_name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    repository = SelectField('Repository to check', coerce=int)
    submit = SubmitField('Submit')

    def validate_internal_name(self, internal_name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=internal_name.data).first()
            if saved_job and saved_job.id != int(self.saved_job_id.data):
                raise ValidationError(f"There already exists a job with name '{internal_name.data}'. Please pick a different name.")


class EditCheckJobForm(FlaskForm):
    saved_job_id = HiddenField('Id')
    internal_name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    repository = SelectField('Repository to check', coerce=int)
    submit = SubmitField('Submit')

    def validate_internal_name(self, internal_name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=internal_name.data).first()
            if saved_job and saved_job.id != int(self.saved_job_id.data):
                raise ValidationError(f"There already exists a job with name '{internal_name.data}'. Please pick a different name.")


class AddPruneJobForm(FlaskForm):
    saved_job_id = HiddenField('Id')
    internal_name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    repository = SelectField('Repository to prune', coerce=int)
    submit = SubmitField('Submit')

    def validate_internal_name(self, internal_name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=internal_name.data).first()
            if saved_job and saved_job.id != int(self.saved_job_id.data):
                raise ValidationError(f"There already exists a job with name '{internal_name.data}'. Please pick a different name.")


class EditPruneJobForm(FlaskForm):
    saved_job_id = HiddenField('Id')
    internal_name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    repository = SelectField('Repository to prune', coerce=int)
    submit = SubmitField('Submit')

    def validate_internal_name(self, internal_name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=internal_name.data).first()
            if saved_job and saved_job.id != int(self.saved_job_id.data):
                raise ValidationError(f"There already exists a job with name '{internal_name.data}'. Please pick a different name.")