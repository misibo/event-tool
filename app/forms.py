from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, ValidationError, SelectMultipleField, TextAreaField, DateTimeField, IntegerField
from wtforms.fields.html5 import EmailField
from wtforms.widgets.core import CheckboxInput
from wtforms.widgets import html_params, HTMLString
from markupsafe import Markup
from wtforms.validators import DataRequired, Length, Email, NumberRange
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


class MultiCheckboxField(SelectMultipleField):

    class CheckboxListWidget(object):

        def __init__(self, stack=True):
            self.stack = stack

        def __call__(self, field, **kwargs):
            kwargs.setdefault('id', field.id)
            html = ['<div %s>' % html_params(**kwargs)]
            for subfield in field:
                class_ = 'uk-checkbox'
                br = '<br>'
                if self.stack is False:
                    br = ''
                else:
                    class_ += ' uk-margin-small-left'
                html.append('%s %s %s' %
                            (subfield(class_=class_), subfield.label, br))
            html.append('</div>')
            return HTMLString(''.join(html))

    widget = CheckboxListWidget()
    option_widget = CheckboxInput()


class GroupEditForm(FlaskForm):
    name = StringField('Name', [DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', [Length(max=1000)])


class EventEditForm(FlaskForm):
    title = StringField('Titel', [DataRequired(), Length(max=100)])
    info = TextAreaField('Info', [Length(max=10000)])
    location = StringField('Standort', [Length(max=100)])
    start = DateTimeField('Start', [DataRequired()])
    end = DateTimeField('Ende')
    equipement = TextAreaField('Ausrüstung')
    cost = IntegerField('Kosten', [NumberRange(min=0)])
    deadline = DateTimeField('Deadline'),
    groups = MultiCheckboxField('Gruppen', [DataRequired()])
