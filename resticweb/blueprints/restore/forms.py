from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, ValidationError, \
    SelectField, TextAreaField, HiddenField


class RestoreFilesForm(FlaskForm):
    file_data = HiddenField('Data')
    destination = StringField('Restore Destination')
    submit = SubmitField('Restore')