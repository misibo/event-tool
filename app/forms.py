from flask import g, session
import hashlib
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from werkzeug.utils import secure_filename
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms import ValidationError, StringField, PasswordField, TextAreaField
from wtforms.fields.html5 import EmailField, DateTimeField, IntegerField
from wtforms.widgets.core import CheckboxInput
from wtforms.widgets import html_params, HTMLString
from wtforms.validators import Optional, DataRequired, Length, Email, NumberRange, Required
from .models import Group, User, db


class LoginForm(FlaskForm):

    username = StringField('Benutzername', [DataRequired()])
    password = PasswordField('Passwort', [DataRequired()])

    def validate(self):
        if not super(LoginForm, self).validate():
            return False
        user = User.query.filter_by(
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
        user = User.query.filter_by(
            id=session['user_id']).first()
        if field.data != user.username and User.query \
                .filter_by(username=field.data).first() is not None:
            raise ValidationError('Benutzername existiert bereits.')


class ChangeEmailForm(FlaskForm):
    old_email = EmailField('Alte E-Mail', [DataRequired(), Email()])
    new_email = EmailField('Neue E-Mail', [DataRequired(), Email()])


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Altes Passwort', [DataRequired()])
    new_password = PasswordField(
        'Neues Passwort', [DataRequired(), Length(min=8)])
    confirm_new_password = PasswordField(
        'Neues Passwort bestätigen', [DataRequired(), Length(min=8)])

    def validate_old_password(self, field):
        user = User.query.filter_by(
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

        username_exists = User.query.filter_by(
            username=self.username.data).first() is not None
        email_exists = User.query.filter_by(
            email=self.email.data).first() is not None

        if not username_exists or not email_exists:
            self.email.errors.append(
                'Es existiert kein Account mit diesem Namen und dieser E-Mail-Adresse.')
            return False

        return True


class ConfirmPasswordResetForm(FlaskForm):
    password = PasswordField('Neues Passwort', [DataRequired(), Length(min=8)])
    password_confirm = PasswordField(
        'Passwort bestätigen', [DataRequired(), Length(min=8)])

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
        user = User.query.filter_by(username=username).first()
        if user is not None:
            raise ValidationError('Benutzername bereits benutzt.')


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

import os


class GroupEditForm(FlaskForm):
    name = StringField('Name', [DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', [Length(max=1000)])
    logo = FileField('Logo', validators=[FileAllowed(['png', 'jpg'])])
    admin = QuerySelectField(
        'Admin',
        # [Required()],
        get_label=lambda user: f'{user.first_name} {user.family_name}',
        # default=g.user,
        query_factory=lambda: User.query.all(),
        allow_blank=True
    )

    def populate_obj(self, group):
        group.name = self.name.data
        group.description = self.description.data
        group.admin = self.admin.data
        if self.logo.data and self.logo.data != group.logo:
            f = self.logo.data
            filename = secure_filename(f.filename)
            # TODO how to determine base path of flask app?
            f.save(os.path.join('app', 'static', 'group', filename))
            group.logo = os.path.join('group', filename)


class EventEditForm(FlaskForm):
    name = StringField('Name', [DataRequired(), Length(max=100)])
    description = TextAreaField('Info', [Length(max=10000)])
    location = StringField('Standort', [DataRequired(), Length(max=100)])
    start = DateTimeField('Start', format='%d.%m.%y %H:%M')
    end = DateTimeField('Ende', format='%d.%m.%y %H:%M')
    equipement = TextAreaField('Ausrüstung', [Optional()])
    cost = IntegerField('Kosten', [Optional(), NumberRange(min=0)])
    deadline = DateTimeField('Deadline', format='%d.%m.%y %H:%M')
    groups = QueryMultiCheckboxField(
        'Gruppen',
        [Required()],
        get_label='name',
        query_factory=lambda: Group.query.all()
    )
    # groups = MultiCheckboxField('Gruppen', [DataRequired()])
