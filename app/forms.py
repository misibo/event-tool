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
import pytz


class LocalDateTimeField(DateTimeField):
    tz = pytz.timezone('Europe/Zurich')

    def process_data(self, value):
        """
        Process the Python data applied to this field and store the result.

        This will be called during form construction by the form's `kwargs` or
        `obj` argument.

        :param value: The python object containing the value to process.
        """
        if value.tzinfo is None:
            raise ValueError('naive datetime is disallowed')
        self.data = value.astimezone(self.tz)

    def process_formdata(self, valuelist):
        """
        Process data received over the wire from a form.

        This will be called during form construction with data supplied
        through the `formdata` argument.

        :param valuelist: A list of strings to process.
        """
        super(LocalDateTimeField, self).process_formdata(valuelist)
        self.data = self.tz.localize(self.data)


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
        if field.data != user.username and db_session.query(User) \
                .filter_by(username=field.data).first() is not None:
            raise ValidationError('Benutzername existiert bereits.')


class ChangeEmailForm(FlaskForm):
    old_email = EmailField('Alte E-Mail', [DataRequired(), Email()])
    new_email = EmailField('Neue E-Mail', [DataRequired(), Email()])


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Altes Passwort', [DataRequired()])
    new_password = PasswordField('Neues Passwort', [DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField(
        'Neues Passwort bestätigen', [DataRequired(), Length(min=8)])

    def validate_old_password(self, field):
        user = db_session.query(User).filter_by(
            id=flask.session['user_id']).first()
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', self.old_password.data.encode('UTF-8'),
            user.password_salt.encode('UTF-8'), 1000)
        if password_hash != user.password_hash:
            raise ValidationError('Altes Passwort ist falsch.')

    def validate(self):
        if not super(ChangePasswordForm, self).validate():
            return False

        if self.new_password.data != self.confirm_new_password.data:
            self.confirm_new_password.errors.append(
                'Bestätigung stimmt nicht mit neuem Passwort überrein.')
            return False

        return True


class ResetPasswordForm(FlaskForm):
    username = StringField('Benutzername', [DataRequired(), Length(max=100)])
    email = EmailField('Email', [DataRequired(), Email()])

    def validate(self):
        if not super(ResetPasswordForm, self).validate():
            return False

        username_exists = db_session.query(User).filter_by(
            username=self.username.data).first() is not None
        email_exists = db_session.query(User).filter_by(
            email=self.email.data).first() is not None

        if not username_exists or not email_exists:
            self.email.errors.append(
                'Es existiert kein Account mit diesem Namen und dieser E-Mail-Adresse.')
            return False

        return True


class ConfirmPasswordResetForm(FlaskForm):
    password = PasswordField('Neues Passwort', [DataRequired(), Length(min=8)])
    password_confirm = PasswordField('Passwort bestätigen', [DataRequired(), Length(min=8)])

    def validate(self):
        if not super(ConfirmPasswordResetForm, self).validate():
            return False

        if self.password.data != self.password_confirm.data:
            self.password_confirm.errors.append(
                'Eingabe stimmt nicht mit überrein.')
            return False

        return True


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
    start = LocalDateTimeField('Start', format='%d.%m.%y %H:%M')
    end = LocalDateTimeField('Ende', format='%d.%m.%y %H:%M')
    equipement = TextAreaField('Ausrüstung', [Optional()])
    cost = IntegerField('Kosten', [Optional(), NumberRange(min=0)])
    deadline = LocalDateTimeField('Deadline', format='%d.%m.%y %H:%M')
    groups = QueryMultiCheckboxField('Gruppen', [Required()], get_label='name')
    # groups = MultiCheckboxField('Gruppen', [DataRequired()])
