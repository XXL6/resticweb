from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, ValidationError, \
    SelectField, TextAreaField, HiddenField, TimeField, BooleanField
from wtforms.validators import DataRequired
from resticweb.tools.local_session import LocalSession
from resticweb.models.general import SavedJobs, Schedule


class AddJobForm(FlaskForm):
    ub_name = StringField('Job Name', validators=[DataRequired()])
    ub_description = TextAreaField('Description')
    submit = SubmitField('Submit')


class AddCheckJobForm(FlaskForm):
    saved_job_id = HiddenField('Id')
    name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    repository = SelectField('Repository to check', coerce=int)
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=name.data).first()
            if saved_job and saved_job.id != int(self.saved_job_id.data):
                raise ValidationError(f"There already exists a job with name '{name.data}'. Please pick a different name.")


class EditCheckJobForm(FlaskForm):
    saved_job_id = HiddenField('Id')
    name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    repository = SelectField('Repository to check', coerce=int)
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=name.data).first()
            if saved_job and saved_job.id != int(self.saved_job_id.data):
                raise ValidationError(f"There already exists a job with name '{name.data}'. Please pick a different name.")


class AddPruneJobForm(FlaskForm):
    saved_job_id = HiddenField('Id')
    name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    repository = SelectField('Repository to prune', coerce=int)
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=name.data).first()
            if saved_job and saved_job.id != int(self.saved_job_id.data):
                raise ValidationError(f"There already exists a job with name '{name.data}'. Please pick a different name.")


class EditPruneJobForm(FlaskForm):
    saved_job_id = HiddenField('Id')
    name = StringField('Job Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    repository = SelectField('Repository to prune', coerce=int)
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            saved_job = session.query(SavedJobs).filter_by(name=name.data).first()
            if saved_job and saved_job.id != int(self.saved_job_id.data):
                raise ValidationError(f"There already exists a job with name '{name.data}'. Please pick a different name.")


class AddScheduleForm(FlaskForm):
    schedule_id = HiddenField('Id')
    name = StringField('Schedule Name', validators=[DataRequired()])
    description = TextAreaField('Description')
    time_interval = IntegerField('Time Interval')
    time_unit = SelectField('Time Unit')
    time_at = TimeField('Time At')
    missed_timeout = IntegerField('Schedule Miss Timeout (minutes)')
    paused = BooleanField('Paused')
    submit = SubmitField('Submit')

    def validate_name(self, name):
        with LocalSession() as session:
            schedule = session.query(Schedule).filter_by(name=name.data).first()
            if schedule and schedule.id != int(self.schedule_id.data):
                raise ValidationError(f"There already exists a schedule with name '{name.data}'. Please pick a different name.")