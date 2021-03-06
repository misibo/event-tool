from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, ValidationError, SelectMultipleField
from wtforms.fields.html5 import EmailField
from wtforms.widgets.core import CheckboxInput
from wtforms.validators import DataRequired, Length, Email
from .models import User, db_session
import hashlib
import flask


class LoginForm(FlaskForm):

    username = StringField('Benutzername', [DataRequired()])
    password = PasswordField('Passwort', [DataRequired()])

    def validate(self):
        if not super(LoginForm, self).validate():
            return False
        user = db_session.query(User).filter_by(
            username=self.username.data).first()
        if user is None:
            self.password.errors.append(
                'Benutzername oder Passwort ist falsch.')
            return False
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', self.password.data.encode('UTF-8'), user.password_salt.encode('UTF-8'), 1000)
        if password_hash != user.password_hash:
            self.password.errors.append(
                'Benutzername oder Passwort ist falsch.')
            return False

        return True


class EditUserForm(FlaskForm):
    username = StringField('Benutzername', [DataRequired(), Length(max=100)])
    email = EmailField('Email', [DataRequired(), Email()])
    first_name = StringField('Vorname', [DataRequired(), Length(max=100)])
    family_name = StringField('Nachname', [DataRequired(), Length(max=100)])

    def validate_username(self, field):
        user = db_session.query(User).filter_by(
            id=flask.session['user_id']).first()
        if field.data != user.username and db_session.query(User).filter_by(username=field.data).first() is not None:
            raise ValidationError('Benutzername existiert bereits.')


class RegisterForm(FlaskForm):

    username = StringField('Benutzername', [DataRequired(), Length(max=100)])
    email = EmailField('Email', [DataRequired(), Email()])
    first_name = StringField('Vorname', [DataRequired(), Length(max=100)])
    family_name = StringField('Nachname', [DataRequired(), Length(max=100)])
    password = PasswordField('Passwort', [DataRequired(), Length(min=8)])

    def validate_username(self, field):
        username = field.data
        user = db_session.query(User).filter_by(username=username).first()
        if user is not None:
            raise ValidationError('Benutzername bereits benutzt.')

class CheckboxListWidget(object):

    def __init__(self, stack=True, prefix_label=True):
        self.html_tag = 'div'
        self.prefix_label = prefix_label

    def __call__(self, field, **kwargs):
        kwargs.setdefault("id", field.id)
        html = ["<%s %s>" % (self.html_tag, html_params(**kwargs))]
        for subfield in field:
            if self.prefix_label:
                html.append("<label>%s %s</label>" % (subfield.label, subfield()))
            else:
                html.append("<label>%s %s</label>" % (subfield(), subfield.label))
        html.append("</%s>" % self.html_tag)
        return Markup("".join(html))

class MultiCheckboxField(SelectMultipleField):
    widget = CheckboxListWidget()
    option_widget = CheckboxInput()

# class FormProject(FlaskForm):
#         Code = StringField(
#             'Code', [Required(message='Please enter your code')])
#         Tasks = MultiCheckboxField('Proses', [Required(message='Please tick your task')], choices=[
#                                     ('nyapu', 'Nyapu'), ('ngepel', 'Ngepel')])
