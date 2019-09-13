import os
from datetime import datetime

import pytz
from flask import flash, g, render_template, request, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from werkzeug.utils import secure_filename
from wtforms import (BooleanField, DateField, HiddenField, PasswordField,
                     SelectField, StringField, TextAreaField, ValidationError)
from wtforms.ext.sqlalchemy.fields import (QuerySelectField,
                                           QuerySelectMultipleField)
from wtforms.fields.html5 import (DateTimeField, EmailField, IntegerField,
                                  TelField)
from wtforms.validators import (DataRequired, Email, Length, NumberRange,
                                Optional, Required)
from wtforms.widgets import HTMLString, html_params
from wtforms.widgets.core import CheckboxInput

from . import mailing
from .models import Group, User


class LocalDateTimeField(DateTimeField):
    tz = pytz.timezone('Europe/Zurich')

    def process_data(self, value):
        """
        Process the Python data applied to this field and store the result.

        This will be called during form construction by the form's `kwargs` or
        `obj` argument.

        :param value: The python object containing the value to process.
        """
        if value is None:
            self.data = value
        else:
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
        user = User.query.filter_by(
            username=self.username.data).first()
        if user is None:
            self.password.errors.append(
                'Benutzername oder Passwort ist falsch.')
            return False
        if not user.validate_password(self.password.data):
            self.password.errors.append(
                'Benutzername oder Passwort ist falsch.')
            return False

        return True


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
        if not g.user.validate_password(field.data):
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

    def validate_username(self, field):
        user = User.query.\
            filter_by(User.username == field.data).\
            first()
        if user is not None:
            raise ValidationError('Benutzername bereits benutzt.')


class AccountForm(RegisterForm):

    image = FileField('Profilbild', [FileAllowed(['png', 'jpg'])])
    birthday = DateField('Geburtstag', [Optional()], format='%d.%m.%y')
    mobile_phone = TelField('Handynummer', [Optional()])
    street = StringField('Strasse', [Optional()])
    postal_code = IntegerField('PLZ', [Optional(), NumberRange(min=1000, max=9658)])
    city = StringField('Ort', [Optional()])

    def validate_username(self, field):
        user = User.query.\
            filter(User.id != g.user.id).\
            filter(User.username == field.data).\
            first()
        if user is not None:
            raise ValidationError('Benutzername bereits benutzt.')

    def populate_obj(self, user):
        user.username = self.username.data
        user.first_name = self.first_name.data
        user.family_name = self.family_name.data
        user.birthday = self.birthday.data
        user.mobile_phone = self.mobile_phone.data
        user.street = self.street.data
        user.postal_code = self.postal_code.data
        user.city = self.city.data
        process_file_upload(self, user, 'image', 'user')


class UserEditForm(AccountForm):

    id = HiddenField()
    permission = SelectField('Rolle', choices=[(enum.name, label) for enum, label in User.get_permission_labels().items()])
    new_password = PasswordField('Neues Passwort', [Optional(), Length(min=8)])
    new_password_confirm = PasswordField('Passwort bestätigen')

    def validate_username(self, field):
        user = User.query.\
                filter(User.id != self.id.data).\
                filter(User.username == field.data).\
                first()
        if user is not None:
            raise ValidationError('Benutzername bereits benutzt.')

    def validate(self):
        if not super(UserEditForm, self).validate():
            return False

        if self.new_password.data and self.new_password.data != self.new_password_confirm.data:
            self.new_password_confirm.errors.append(
                'Passwörter stimmen nicht überein.')
            return False

        return True

    def populate_obj(self, user):
        user.username = self.username.data
        user.first_name = self.first_name.data
        user.family_name = self.family_name.data
        user.email = self.email.data
        user.set_password(self.new_password.data)
        user.birthday = self.birthday.data
        # TODO: how to assign new permission?
        # user.permission = User.Permission(self.permission.data)
        user.mobile_phone = self.mobile_phone.data
        user.street = self.street.data
        user.postal_code = self.postal_code.data
        user.city = self.city.data
        process_file_upload(self, user, 'image', 'user')


class ConfirmRegistrationForm(FlaskForm):
    username = StringField('Benutzername')  # read-only, needed for password-managers
    password = PasswordField('Passwort', [DataRequired(), Length(min=8)])
    password_confirm = PasswordField('Passwort bestätigen', [DataRequired(), Length(min=8)])

    def validate(self):
        if not super(ConfirmRegistrationForm, self).validate():
            return False

        if self.password.data != self.password_confirm.data:
            self.password_confirm.errors.append(
                'Eingabe stimmt nicht mit überrein.')
            return False

        return True


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


# process file if uploaded via form
def process_file_upload(form, model, attr, directory):
    f = getattr(form, attr).data
    if f and f != getattr(model, attr):
        filename = secure_filename(f.filename)
        # TODO how to determine base path of flask app?
        f.save(os.path.join('app', 'static', directory, filename))
        setattr(model, attr, os.path.join(directory, filename))


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
        allow_blank=True,
        blank_text='- Auswählen -'
    )

    def populate_obj(self, group):
        group.name = self.name.data
        group.description = self.description.data
        group.admin = self.admin.data
        process_file_upload(self, group, 'logo', 'group')


class EventEditForm(FlaskForm):
    name = StringField('Name', [DataRequired(), Length(max=100)])
    description = TextAreaField('Info', [Length(max=10000)])
    location = StringField('Standort', [DataRequired(), Length(max=100)])
    start = LocalDateTimeField('Start', format='%d.%m.%y %H:%M')
    end = LocalDateTimeField('Ende', format='%d.%m.%y %H:%M')
    equipment = TextAreaField('Ausrüstung', [Optional()])
    cost = IntegerField('Kosten', [Optional(), NumberRange(min=0)])
    deadline = LocalDateTimeField('Deadline für Anmeldung', format='%d.%m.%y %H:%M')
    image = FileField('Image', validators=[FileAllowed(['png', 'jpg'])])
    groups = QueryMultiCheckboxField(
        'Gruppen',
        [Required()],
        get_label='name',
        query_factory=lambda: Group.query.all()
    )

    def populate_obj(self, event):
        event.name = self.name.data
        event.description = self.description.data
        event.location = self.location.data
        event.start = self.start.data
        event.end = self.end.data
        event.equipment = self.equipment.data
        event.cost = self.cost.data
        event.deadline = self.deadline.data
        event.groups = self.groups.data
        process_file_upload(self, event, 'image', 'event')


class EditInvitationForm(FlaskForm):
    accepted = BooleanField("Einladung akzeptieren")
    num_friends = IntegerField("Anzahl Freunde")
    num_car_seats = IntegerField("Anzahl Fahrplätze")

    def validate_num_friends(self, field):
        if field.data is not None and field.data < 0:
            raise ValidationError('Anzahl Freunde muss grösser oder gleich 0 sein.')

    def validate_num_car_seats(self, field):
        if field.data is not None and field.data < 0:
            raise ValidationError('Anzahl Fahrplätze muss grösser oder gleich 0 sein.')

    def validate(self):
        if not super(EditInvitationForm, self).validate():
            return False

        error = False
        if self.accepted.data is not True:
            if self.num_friends.data not in (None, 0):
                self.num_friends.errors.append(
                    'Du kannst keine Freunde einladen, wenn du dich nicht anmeldest.')
                error = True
            if self.num_car_seats.data not in (None, 0):
                self.num_car_seats.errors.append(
                    'Du kannst keine Fahrplätze zur Verfügung stellen, wenn du dich nicht anmeldest.')
                error = True
        return not error
