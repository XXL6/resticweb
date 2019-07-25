from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, \
    FieldList, FormField, HiddenField, TextField
from wtforms.validators import DataRequired, EqualTo, ValidationError
from resticweb.blueprints.users.models import User


class UpdateAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password')
    confirm_password = PasswordField('Confirm Password', validators=[EqualTo('password')])
    submit = SubmitField('Submit')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError("Username already in use. Choose a different one.")


class UnlockCredentialStoreForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class EncryptCredentialStoreForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[EqualTo('password')])
    submit = SubmitField('Submit')


class DecryptCredentialStoreForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class CredentialsForm(FlaskForm):
    credential = StringField()
    credential_role = HiddenField()


class EditCredentialsForm(FlaskForm):
    group_description = StringField('Group Description')
    group_credentials = FieldList(FormField(CredentialsForm))
    submit = SubmitField('Submit')

    def append_field(self, label, data):
        for credential_form in self.group_credentials:
            if credential_form.credential_role == "":
                credential_form.credential_role = label
                credential_form.credential.data = data
                credential_form.credential.label.text = label
