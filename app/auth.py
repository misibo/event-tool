
import functools
import uuid
import hashlib
import os
from datetime import datetime, timedelta
from flask import Blueprint, g, session, render_template, url_for, redirect, flash, request, escape
from flask_mail import Message
from .models import PendingUser, User, db_session
from .forms import (
    RegisterForm, LoginForm, ChangePasswordForm, ResetPasswordForm,
    ConfirmPasswordResetForm)
import app as root

bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder='templates/auth')


def close_session():
    for key in {'user_id', 'timestamp'}:
        if key in session:
            session.pop(key)


def create_session(user_id):
    close_session()
    created_at = datetime.utcnow()
    session['user_id'] = user_id
    session['timestamp'] = f'{created_at:%Y-%m-%d %H:%M:%S}'


def is_session_active():
    return all(key in session for key in {'user_id', 'timestamp'})


# def with_checked_session(callback):
#     app.logger.warning(flask.session)
#     if is_session_active():
#         timestamp = datetime.datetime.strptime(
#             flask.session['timestamp'], '%Y-%m-%d %H:%M:%S')
#         if not (timestamp <= datetime.datetime.utcnow() < \
#                 timestamp + datetime.timedelta(hours=2)):
#             # timestamp has expired
#             return flask.redirect(flask.url_for('login', redirect=flask.request.url))

#         user = db_session.query(User).filter_by(
#             id=flask.session['user_id']).first()
#         if user is None:
#             # user has been deleted
#             return flask.redirect(flask.url_for('login', redirect=flask.request.url))

#         return callback(user)
#     else:
#         return flask.redirect(flask.url_for('login', redirect=flask.request.url))

def login_required(view):

    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view


@bp.before_app_request
def load_logged_in_user():
    if is_session_active():
        timestamp = datetime.strptime(
            session['timestamp'], '%Y-%m-%d %H:%M:%S')
        if not (timestamp <= datetime.utcnow() < timestamp + timedelta(hours=2)):
            g.user = None
        g.user = db_session.query(User).filter_by(
            id=session['user_id']).first()
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
        salt = str(uuid.uuid4())
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', form.password.data.encode('UTF-8'), salt.encode('UTF-8'), 1000)

        token = os.urandom(16).hex()

        user = PendingUser(
            confirm_token=token,
            username=form.username.data,
            first_name=form.first_name.data,
            family_name=form.family_name.data,
            email=form.email.data,
            password_salt=salt,
            password_hash=password_hash,
            insertion_time_utc=datetime.utcnow(),
        )
        db_session.add(user)
        db_session.commit()

        msg = Message(
            "Please register",
            sender="root@localhost",
            recipients=[user.email])

        confirm_url = request.url_root + url_for('auth.confirm', token=token)[1:]

        msg.body = (
            f'Hallo {escape(user.username)}, \n'
            f'Du hast dich erfolgreich registriert. '
            f'Bitte klicke auf folgenden Link, um die E-Mail Adresse zu bestätigen: {confirm_url}'
        )
        root.app.logger.info(f'{user.email} can confirmed by {confirm_url}')

        try:
            root.mail.send(msg)
        except Exception:
            root.app.logger.exception('Could not delivery e-mail.')
            flash((
                'Beim Versenden der E-Mail ist ein Fehler aufgetreten, '
                'deshalb wirst du wahrscheinlich keine E-Mail erhalten. '
                'Bitte überprüfe die E-Mail-Adresse auf Tippfehler.'),
                'error')
        else:
            flash((
                'Du wirst in Kürze eine E-Mail mit einem Link erhalten, '
                'um den Account zu aktivieren.'),
                'info')

        # TODO: Implement page to explain what the user has to do now

    return render_template('register.html', form=form)


@bp.route('/confirm', methods=['GET', 'POST'])
def confirm():
    close_session()

    token = str(request.args.get('token', 'invalid'))

    temp: PendingUser = db_session.query(PendingUser).filter_by(
        confirm_token=token).first()

    if temp is None:
        flash((
            'Die Aktivierung ist fehlgeschlagen, '
            'weil der Link in der E-Mail ungültig ist. '
            'Bitte registriere dich neu, um eine neue E-Mail zu erhalten.'),
            'error')
        return redirect(url_for('auth.register'))
    else:
        # check for existing users
        existing_user = db_session.query(User).filter_by(username=temp.username).first()
        expiry_date = temp.insertion_time_utc + timedelta(days=1)

        if existing_user is not None:
            flash(('Der Account wurde bereits aktiviert. Versuche dich anmelden.'), 'info')
            return redirect(url_for('auth.login'))
        elif not(temp.insertion_time_utc <= datetime.utcnow() < expiry_date):
            flash((
                'Die Aktivierung ist fehlgeschlagen, '
                'weil der Link in der E-Mail abgelaufen ist. '
                'Bitte registriere dich neu, um eine neue E-Mail zu erhalten.'),
                'error')
            return redirect(url_for('auth.register'))
        else:
            # create real user
            user = User(
                username=temp.username,
                email=temp.email,
                first_name=temp.first_name,
                family_name=temp.family_name,
                password_salt=temp.password_salt,
                password_hash=temp.password_hash,
            )
            db_session.add(user)
            db_session.commit()

            flash('E-Mail-Adresse erfolgreich bestätigt. Du kannst dich jetzt anmelden.', 'info')
            return redirect(url_for('auth.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()

    if form.validate_on_submit():
        user = db_session.query(User).filter_by(
            username=form.username.data).first()
        create_session(user.id)
        flash('Du hast dich erfolgreich angemeldet.')
        return redirect(url_for('account'))

    return render_template('login.html', form=form)


@bp.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        user = db_session.query(User).filter_by(
            id=session['user_id']).first()
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', form.new_password.data.encode('UTF-8'),
            user.password_salt.encode('UTF-8'), 1000)
        user.password_hash = password_hash
        db_session.commit()

        flash('Passwort wurde erfolgreich geändert.')
        return redirect(url_for('account'))

    return render_template('user/password.html', form=form)


@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    close_session()

    form = ResetPasswordForm()

    if form.validate_on_submit():
        token = os.urandom(16).hex()

        username = form.username.data
        email = form.email.data

        user: User = db_session.query(User).filter_by(username=username, email=email).first()

        user.password_reset_token = token
        user.password_reset_insertion_time_utc = datetime.utcnow()
        db_session.commit()

        confirm_url = request.url_root + url_for('auth.confirm_password_reset', token=token)[1:]

        msg = Message(
            "Please register",
            sender="root@localhost",
            recipients=[email])

        msg.body = (
            f'Bitte klicke auf folgenden Link, um das Passwort zurückzusetzen: {confirm_url}'
        )
        root.app.logger.info(f'The password of {username} is reset by {confirm_url}')

        try:
            root.mail.send(msg)
        except Exception:
            root.app.logger.exception('Could not delivery e-mail.')
            flash((
                'Beim Versenden der E-Mail ist ein Fehler aufgetreten, '
                'deshalb wirst du wahrscheinlich keine E-Mail erhalten. '
                'Bitte kontaktiere einen Admin.'),
                'error')
        else:
            flash((
                'Du wirst in Kürze eine E-Mail mit einem Link erhalten, '
                'um das Passwort zurücksusetzen.'),
                'info')

    return render_template('auth/reset_password.html', form=form)


@bp.route('/confirm_password_reset', methods=['GET', 'POST'])
def confirm_password_reset():
    close_session()

    token = request.args.get('token', 'invalid')

    user: User = db_session.query(User).filter_by(password_reset_token=token).first()

    if user is None:
        flash((
            'Das Passwort konnte nicht zurückgesetzt werden, weil der Link ungültig ist. '
            'Bitte versuche erneut, das Passwort zurückzusetzen.'), 'error')
        return redirect(url_for('auth.reset_password'))
    else:
        insertion_time = user.password_reset_insertion_time_utc
        expiry_date = user.password_reset_insertion_time_utc + timedelta(hours=2)

        if not(insertion_time <= datetime.utcnow() < expiry_date):
            flash((
                'Das Passwort konnte nicht zurückgesetzt werden, weil der Link abgelaufen ist. '
                'Bitte versuche erneut, das Passwort zurückzusetzen.'), 'error')
            return redirect(url_for('auth.reset_password'))
        else:
            form = ConfirmPasswordResetForm()

            if form.validate_on_submit():
                assert token == user.password_reset_token

                user.password_hash = hashlib.pbkdf2_hmac(
                    'sha256', form.password.data.encode('UTF-8'),
                    user.password_salt.encode('UTF-8'), 1000)
                user.password_reset_token = None
                user.password_reset_insertion_time_utc = None
                db_session.commit()

                flash((
                    'Das Passwort wurde erfolgreich zurückgesetzt. '
                    'Du kannst dich jetzt mit dem neuen Passwort anmelden.'), 'info')
                return redirect(url_for('auth.login'))
            else:
                return render_template('auth/confirm_password_reset.html', form=form)


@bp.route('/logout')
def logout():
    close_session()
    return redirect(url_for('index'))
