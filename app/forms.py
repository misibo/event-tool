import os
from datetime import datetime

import pytz
from flask import current_app, flash, g, render_template, request, url_for
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from PIL import Image
from slugify import slugify
from werkzeug.utils import secure_filename
from wtforms import (BooleanField, DateField, HiddenField, PasswordField,
                     RadioField, SelectField, StringField, TextAreaField,
                     ValidationError)
from wtforms.ext.sqlalchemy.fields import (QuerySelectField,
                                           QuerySelectMultipleField)
from wtforms.fields.html5 import (DateTimeField, EmailField, IntegerField,
                                  TelField)
import wtforms.validators
from wtforms.validators import (Email, Length, NumberRange,
                                Optional, Required)
from wtforms.widgets import HTMLString, html_params
from wtforms.widgets.core import CheckboxInput

from . import mail
from .models import Event, Group, GroupMember, Participant, User
from .utils import tz, now


def DataRequired():
    # Note: the "message" parameter to DataRequired is ignored by browsers that support HTML5.
    # It's not trivial to override the default.
    return wtforms.validators.DataRequired()


def LogoFileField(title):
    return FileField(f"{title} (PNG)")


def PhotographyFileField(title):
    return FileField(f"{title} (JPEG)")


def FlyerFileField(title):
    return FileField(f"{title} (PDF)")


class LocalDateTimeField(DateTimeField):

    tz = tz

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


class RadioListWidget(object):

    def __init__(self, stack=True):
        self.stack = stack

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        html = ['<div %s>' % html_params(**kwargs)]
        for subfield in field:
            class_ = 'uk-radio'
            br = '<br>'
            if self.stack is False:
                br = ''
            else:
                class_ += ' uk-margin-small-left'
            html.append('%s %s %s' %
                        (subfield(class_=class_), subfield.label, br))
        html.append('</div>')
        return HTMLString(''.join(html))


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
        user = User.query.filter_by(username=field.data).first()
        if user is not None:
            raise ValidationError('Benutzername bereits benutzt.')

    def populate_obj(self, user: User):
        user.username = self.username.data
        user.email = self.email.data
        user.first_name = self.first_name.data
        user.family_name = self.family_name.data

class AccountForm(RegisterForm):

    avatar = LogoFileField('Profilbild')
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

    def populate_obj(self, user: User):
        super().populate_obj(user)
        user.modified = now
        user.birthday = self.birthday.data
        user.mobile_phone = self.mobile_phone.data
        user.street = self.street.data
        user.postal_code = self.postal_code.data
        user.city = self.city.data

        if self.avatar.data is not None:
            user.save_avatar(self.avatar.data)


class UserEditForm(AccountForm):

    id = HiddenField()
    url_back = HiddenField()
    role = SelectField('Rolle', choices=User.Role.get_select_choices(), coerce=int)
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

    def populate_obj(self, user: User):
        super().populate_obj(user)

        user.role = self.role.data
        user.email = self.email.data

        if self.new_password.data:
            user.set_password(self.new_password.data)


class ConfirmRegistrationForm(FlaskForm):

    username = StringField('Benutzername')
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


class GroupEditForm(FlaskForm):

    url_back = HiddenField()
    name = StringField('Name', [DataRequired(), Length(max=100)])
    slug = StringField('Slug')
    abstract = TextAreaField('Kurzinfo')
    details = TextAreaField('Details')
    logo = LogoFileField('Logo')
    background = PhotographyFileField('Hintergrund')
    flyer = FlyerFileField('Flyer')

    def populate_obj(self, group):
        group.name = self.name.data
        group.abstract = self.abstract.data
        group.details = self.details.data
        group.slug = slugify(self.slug.data if self.slug.data else group.name)
        if self.logo.data is not None:
            group.save_logo(self.logo.data)
        if self.background.data is not None:
            group.save_background(self.background.data)
        if self.flyer.data is not None:
            group.save_flyer(self.flyer.data)


class EventEditForm(FlaskForm):

    url_back = HiddenField()
    name = StringField('Name', [DataRequired(), Length(max=100)])
    abstract = TextAreaField('Kurzinfo', [Length(max=10000)])
    details = TextAreaField('Details', [Length(max=10000)])
    location = StringField('Standort', [DataRequired(), Length(max=100)])
    start = LocalDateTimeField('Start', format='%d.%m.%y %H:%M')
    end = LocalDateTimeField('Ende', format='%d.%m.%y %H:%M')
    equipment = TextAreaField('Ausrüstung', [Optional()])
    cost = IntegerField('Kosten', [Optional(), NumberRange(min=0)])
    registration_start = LocalDateTimeField('Anmeldestart', format='%d.%m.%y %H:%M', validators=[Optional()])
    deadline = LocalDateTimeField('Anmeldeschluss', format='%d.%m.%y %H:%M')
    background = PhotographyFileField('Hintergrund')
    groups = QuerySelectMultipleField(
        'Gruppen',
        [Required()],
        get_label='name',
        query_factory=lambda: Group.query.all(),
        widget=CheckboxListWidget(),
        option_widget=CheckboxInput()
    )

    def validate(self):
        if not super(EventEditForm, self).validate():
            return False

        error = False

        if self.start.data > self.end.data:
            self.start.errors.append('Start muss vor dem Ende sein.')
            error = True

        if self.deadline.data > self.start.data:
            self.deadline.errors.append('Deadline muss vor dem Start sein.')
            error = True

        return not error

    def populate_obj(self, event):
        super().populate_obj(event)
        if self.background.data is not None:
            event.save_background(self.background.data)


class ConfirmForm(FlaskForm):
    url_back = HiddenField()


class EditParticipantForm(FlaskForm):

    url_back = HiddenField()
    registration_status = SelectField('Teilnahmestatus', choices=Participant.RegistrationStatus.get_select_choices(), coerce=int)
    num_friends = IntegerField("Anzahl Freunde")
    num_car_seats = IntegerField("Anzahl Fahrplätze")

    def validate_num_friends(self, field):
        if field.data is not None and field.data < 0:
            raise ValidationError('Anzahl Freunde muss grösser oder gleich 0 sein.')

    def validate_num_car_seats(self, field):
        if field.data is not None and field.data < 0:
            raise ValidationError('Anzahl Fahrplätze muss grösser oder gleich 0 sein.')

    def validate(self):
        if not super(EditParticipantForm, self).validate():
            return False

        error = False

        if self.registration_status.data != Participant.RegistrationStatus.REGISTERED:
            if self.num_friends.data > 0:
                self.num_friends.errors.append(
                    'Du kannst keine Freunde einladen, wenn du dich nicht anmeldest.')
                error = True
            if self.num_car_seats.data > 0:
                self.num_car_seats.errors.append(
                    'Du kannst keine Fahrplätze zur Verfügung stellen, wenn du dich nicht anmeldest.')
                error = True

        return not error

class GroupMemberForm(FlaskForm):

    role = SelectField(
        'Rolle',
        choices=GroupMember.Role.get_select_choices(),
        coerce=int
    )

    def adapt_role_choices(self, can_manage):
        if not can_manage:
            del(self.role.choices[2])

class EventMailForm(FlaskForm):
    event_details = TextAreaField('Details des Anlasses anpassen')
    annotation = TextAreaField('Anmerkung')
