from flask_wtf import FlaskForm
from wtforms import ValidationError, StringField, PasswordField, SelectMultipleField, TextAreaField
from wtforms.fields.html5 import EmailField, DateTimeField, IntegerField
from wtforms.widgets.core import CheckboxInput
from wtforms.widgets import html_params, HTMLString
from markupsafe import Markup
from wtforms.validators import Optional, DataRequired, Length, Email, NumberRange, Required
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

from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField

# class MultiCheckboxField(SelectMultipleField):
class QueryMultiCheckboxField(QuerySelectMultipleField):

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
    name = StringField('Name', [DataRequired(), Length(max=100)])
    description = TextAreaField('Info', [Length(max=10000)])
    location = StringField('Standort', [DataRequired(), Length(max=100)])
    # https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior
    start = DateTimeField('Start', format='%d.%m.%y %H:%M')
    end = DateTimeField('Ende', format='%d.%m.%y %H:%M')
    equipement = TextAreaField('Ausrüstung', [Optional()])
    cost = IntegerField('Kosten', [Optional(), NumberRange(min=0)])
    deadline = DateTimeField('Deadline', format='%d.%m.%y %H:%M')
    groups = QueryMultiCheckboxField('Gruppen', [Required()], get_label='name')
    # groups = MultiCheckboxField('Gruppen', [DataRequired()])
