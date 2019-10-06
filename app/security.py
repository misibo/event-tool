import functools
import os
from datetime import datetime, timedelta

import pytz
import flask
from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, session, url_for)
from itsdangerous import BadSignature

from . import mailing
from .forms import (ChangeEmailForm, ChangePasswordForm,
                    ConfirmPasswordResetForm, ConfirmRegistrationForm,
                    LoginForm, RegisterForm, ResetPasswordForm)
from .models import User, db

bp = Blueprint("security", __name__)


def close_session():
    for key in {'user_id', 'timestamp'}:
        if key in session:
            session.pop(key)


def create_session(user_id):
    close_session()
    created_at = pytz.utc.localize(datetime.utcnow())
    session['user_id'] = user_id
    session['timestamp'] = f'{created_at:%Y-%m-%d %H:%M:%S}'


def is_session_active():
    return all(key in session for key in {'user_id', 'timestamp'})


def login_required(view, privilege=User.Role.USER):

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        disable_auth = bool(current_app.config.get('DISABLE_AUTH', False))

        if os.environ['FLASK_ENV'] != 'development':
            # prevent disabling authentication by accident
            disable_auth = False

        if disable_auth:
            return view(**kwargs)

        if g.user is None:
            # not logged in
            return redirect(url_for('security.login', redirect_url=request.url))

        assert privilege in {User.Role.USER, User.Role.MANAGER, User.Role.ADMIN}
        if g.user.role < privilege:
            return flask.abort(403)  # forbidden

        return view(**kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    if is_session_active():
        timestamp = pytz.utc.localize(datetime.strptime(session['timestamp'], '%Y-%m-%d %H:%M:%S'))
        if not (timestamp <= pytz.utc.localize(datetime.utcnow()) < timestamp + timedelta(hours=2)):
            g.user = None
        g.user = User.query.\
            filter(User.id == session['user_id']).\
            first()
        # if user is None:
        #     # user has been deleted
        #     return flask.redirect(flask.url_for('login', redirect=flask.request.url))
    else:
        g.user = None


@bp.route('/register', methods=['GET', 'POST'])
def register():
    close_session()

    form = RegisterForm()

    if form.validate_on_submit():
        token = current_app.secure_serializer.dumps({
            'username': form.username.data,
            'first_name': form.first_name.data,
            'family_name': form.family_name.data,
            'email': form.email.data,
            'timestamp': f'{datetime.utcnow():%Y-%m-%d %H:%M:%S}',
        })

        confirm_url = request.url_root + url_for('security.confirm', token=token)[1:]
        current_app.logger.info(f'{form.email.data,} can confirmed by {confirm_url}')

        success = mailing.send_single_mail(
            recipient=form.email.data,
            subject="Registrierung",
            text=render_template(
                'mail/confirm_registration.text',
                user=form.first_name.data, confirm_url=confirm_url),
            html=render_template(
                'mail/confirm_registration.html',
                user=form.first_name.data, confirm_url=confirm_url),
        )

        if not success:
            current_app.logger.exception('Could not delivery e-mail.')
            flash((
                'Beim Versenden der E-Mail ist ein Fehler aufgetreten. '
                'Bitte überprüfe die E-Mail-Adresse auf Tippfehler.'),
                'error')
        else:
            flash((
                'Du wirst in Kürze eine E-Mail mit einem Link erhalten, '
                'um die Registrierung abzuschliessen.'),
                'info')

        # TODO: Implement page to explain what the user has to do now

    return render_template('security/register.html', form=form)


@bp.route('/confirm', methods=['GET', 'POST'])
def confirm():
    close_session()

    token = request.args.get('token', 'invalid')

    try:
        payload = current_app.secure_serializer.loads(token)
    except BadSignature:
        flash((
            'Die Aktivierung ist fehlgeschlagen, '
            'weil der Link in der E-Mail ungültig ist. '
            'Bitte registriere dich neu, um eine neue E-Mail zu erhalten.'),
            'error')
        return redirect(url_for('security.register'))
    else:
        existing_user = User.query.filter_by(username=payload['username']).first()
        timestamp = pytz.utc.localize(datetime.strptime(payload['timestamp'], '%Y-%m-%d %H:%M:%S'))

        if existing_user is not None:
            flash('Der Account wurde bereits aktiviert.', 'info')
            return redirect(url_for('security.login'))
        elif not (timestamp <= pytz.utc.localize(datetime.utcnow()) < timestamp + timedelta(days=1)):
            flash((
                'Die Aktivierung ist fehlgeschlagen, '
                'weil der Link in der E-Mail abgelaufen ist. '
                'Bitte registriere dich neu, um eine neue E-Mail zu erhalten.'),
                'error')
            return redirect(url_for('security.register'))
        else:
            form = ConfirmRegistrationForm(username=payload['username'])

            if not form.validate_on_submit():
                return render_template('security/confirm_registration.html', form=form)
            else:
                # create real user
                user = User(
                    username=payload['username'],
                    email=payload['email'],
                    first_name=payload['first_name'],
                    family_name=payload['family_name']
                )
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()

                flash('E-Mail-Adresse erfolgreich bestätigt. Du kannst dich jetzt anmelden.', 'info')
                return redirect(url_for('security.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(
            username=form.username.data).first()
        create_session(user.id)
        flash('Du hast dich erfolgreich angemeldet.')

        redirect_url = request.args.get('redirect_url')
        if redirect_url is None:
            return redirect(url_for('dashboard.upcoming'))
        else:
            return redirect(redirect_url)

    return render_template('security/login.html', form=form)


@bp.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        g.user.set_password(form.new_password.data)
        db.session.commit()

        flash('Passwort wurde erfolgreich geändert.')
        return redirect(url_for('dashboard.upcoming'))

    return render_template('user/password.html', form=form)


@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    close_session()

    form = ResetPasswordForm()

    if form.validate_on_submit():
        token = os.urandom(16).hex()

        username = form.username.data
        email = form.email.data

        user: User = User.query.filter_by(
            username=username, email=email).first()

        user.password_reset_token = token
        user.password_reset_insertion_time_utc = pytz.utc.localize(datetime.utcnow())
        db.session.commit()

        confirm_url = request.url_root + \
            url_for('security.confirm_password_reset', token=token)[1:]
        current_app.logger.info(
            f'The password of {username} is reset by {confirm_url}')

        success = mailing.send_single_mail(
            recipient=email,
            subject='Passwort zurücksetzen',
            text=render_template('mail/reset_password.text',
                                 user=user, confirm_url=confirm_url),
            html=render_template('mail/reset_password.html',
                                 user=user, confirm_url=confirm_url),
        )

        if not success:
            flash((
                'Beim Versenden der E-Mail ist ein Fehler aufgetreten. '
                'Möglicherweise ist die E-Mail-Adresse ungültig.'),
                'error')
        else:
            flash((
                'Du wirst in Kürze eine E-Mail mit einem Link erhalten, '
                'um das Passwort zurückzusetzen.'),
                'info')

    return render_template('security/reset_password.html', form=form)


@bp.route('/confirm_password_reset', methods=['GET', 'POST'])
def confirm_password_reset():
    close_session()

    token = request.args.get('token', 'invalid')

    user: User = User.query.filter_by(
        password_reset_token=token).first()

    if user is None:
        flash((
            'Das Passwort kann nicht zurückgesetzt werden, '
            'weil der Link bereits verwendet wurde, oder ungültig ist. '
            'Bitte fordere erneut eine E-Mail an.'), 'error')
        return redirect(url_for('security.reset_password'))
    else:
        insertion_time = user.password_reset_insertion_time_utc
        expiry_date = user.password_reset_insertion_time_utc + \
            timedelta(hours=2)

        if not(insertion_time <= pytz.utc.localize(datetime.utcnow()) < expiry_date):
            flash((
                'Das Passwort kann nicht zurückgesetzt werden, weil der Link abgelaufen ist, '
                'und deshalb nicht mehr verwendet werden kann. '
                'Bitte fordere erneut eine E-Mail an.'), 'error')
            return redirect(url_for('security.reset_password'))
        else:
            form = ConfirmPasswordResetForm()

            if form.validate_on_submit():
                assert token == user.password_reset_token

                user.set_password(form.password.data)
                user.password_reset_token = None
                user.password_reset_insertion_time_utc = None
                db.session.commit()

                flash((
                    'Das Passwort wurde erfolgreich geändert. '
                    'Melde dich jetzt mit dem neuen Passwort an.'), 'info')
                return redirect(url_for('security.login'))
            else:
                return render_template('security/confirm_password_reset.html', form=form)


@bp.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email():
    user = g.user
    form = ChangeEmailForm(old_email=user.email)

    if form.validate_on_submit():
        token = os.urandom(16).hex()

        user.email_change_request = new_email
        user.email_change_insertion_time_utc = pytz.utc.localize(datetime.utcnow())
        user.email_change_token = token

        confirm_url = request.url_root + \
            url_for('security.confirm_email', token=token)[1:]

        # current_app.logger.info(
        #     f'New email address is activated by {confirm_url}')

        success = mailing.send_single_mail(
            recipient=user.email_change_request,
            subject='E-Mail-Adresse ändern',
            text=render_template('mail/change_email.text',
                                    user=user, confirm_url=confirm_url),
            html=render_template('mail/change_email.html',
                                    user=user, confirm_url=confirm_url),
        )

        if not success:
            flash((
                'Beim Versenden des Bestätigungs-Link '
                'an die neue E-Mail-Adresse ist ein Fehler aufgetreten. '
                'Möglicherweise enthält die Adresse ein Tippfehler.'),
                'error')
        else:
            flash((
                'Es wurde eine Mail mit einem Bestätigungs-Link '
                'an die neue E-Mail-Addresse verschickt.'),
                'info')
        db.session.commit()

    return render_template('user/email.html', form=form)


@bp.route('/confirm_email', methods=['GET', 'POST'])
def confirm_email():
    token = str(request.args.get('token', 'invalid'))

    user: User = User.query.filter_by(
        email_change_token=token).first()

    if user is None:
        flash((
            'Das E-Mail-Adresse konnte nicht geändert werden, '
            'weil der Link ungültig ist, oder bereits verwendet wurde.'), 'error')
        return redirect(url_for('dashboard.upcoming'))
    else:
        insertion_time = user.email_change_insertion_time_utc
        expiry_date = user.email_change_insertion_time_utc + timedelta(hours=2)

        if not(insertion_time <= pytz.utc.localize(datetime.utcnow()) < expiry_date):
            flash((
                'Das E-Mail-Adresse konnte nicht geändert werden, '
                'weil der Link abgelaufen ist. '), 'error')
            return redirect(url_for('dashboard.upcoming'))
        else:
            user.email = user.email_change_request
            user.email_change_insertion_time_utc = None
            user.email_change_request = None
            user.email_change_token = None
            db.session.commit()

            flash((
                'Die neue E-Mail-Adresse wurde erfolgreich aktiviert'),
                'info')
            return redirect(url_for('dashboard.upcoming'))


@bp.route('/logout')
def logout():
    close_session()
    return redirect(url_for('index'))
