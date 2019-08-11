import flask
from flask import request, url_for
from .forms import EditUserForm
from .models import db_session, User
from . import auth
import app.mailing as mailing
from datetime import datetime
import os
from flask_mail import Mail

app = flask.Flask(__name__, instance_relative_config=True)
app.config.from_object('config')  # load ./config.py
app.config.from_pyfile('config.py')  # load ./instance/config.py
mail = Mail(app)

app.secret_key = b'misibo'  # os.urandom(16)


# def close_session():
#     for key in {'user_id', 'timestamp'}:
#         if key in flask.session:
#             flask.session.pop(key)


# def create_session(user_id):
#     close_session()
#     created_at = datetime.datetime.utcnow()
#     flask.session['user_id'] = user_id
#     flask.session['timestamp'] = f'{created_at:%Y-%m-%d %H:%M:%S}'


# def is_session_active():
#     return all(key in flask.session for key in {'user_id', 'timestamp'})


# def with_checked_session(callback):
#     app.logger.warning(flask.session)
#     if is_session_active():
#         timestamp = datetime.datetime.strptime(
#             flask.session['timestamp'], '%Y-%m-%d %H:%M:%S')
#         if not (timestamp <= datetime.datetime.utcnow() < timestamp + datetime.timedelta(hours=2)):
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

app.register_blueprint(auth.bp)


@app.route('/', methods=['GET', 'POST'])
def index():
    return flask.render_template('home.html')


@app.route('/account/', methods=['GET', 'POST'])
@auth.login_required
def account():
    user: User = flask.g.user
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.first_name = form.first_name.data
        user.family_name = form.family_name.data

        if user.email != form.email.data:
            token = os.urandom(16).hex()

            user.email_change_request = form.email.data
            user.email_change_insertion_time_utc = datetime.utcnow()
            user.email_change_token = token

            confirm_url = request.url_root + url_for('auth.confirm_changed_email', token=token)[1:]

            app.logger.info(f'New email address is activated by {confirm_url}')

            success = mailing.send_single_mail(
                user.email_change_request, 'E-Mail Bestätigung',
                text=(
                    f'Hallo {user.first_name}, \n',
                    f'Du hast die im Account die E-Mail-Adresse geändert. ',
                    f'Klicke auf folgenden Link, '
                    f'um die neue E-Mail-Adresse zu bestätigen: {confirm_url}'
                ))

            if not success:
                flask.flash((
                    'Beim Versenden des Bestätigungs-Link '
                    'an die neue E-Mail-Adresse ist ein Fehler aufgetreten. '
                    'Möglicherweise enthält die Adresse ein Tippfehler.'),
                    'info')
            else:
                flask.flash((
                    'Es wurde eine Mail mit einem Bestätigungs-Link '
                    'an die neue E-Mail-Addresse verschickt.'),
                    'info')

        db_session.commit()

        flask.flash('Profil erfolgreich angepasst.')

    return flask.render_template('user/edit.html', form=form)


# @app.route('/login/', methods=['GET', 'POST'])
# def login():

#     form = LoginForm()

#     if form.validate_on_submit():
#         user = db_session.query(User).filter_by(
#             username=form.username.data).first()
#         create_session(user.id)
#         flask.flash('Du hast dich erfolgreich eingeloggt.')
#         return flask.redirect(flask.url_for('account'))

#     return flask.render_template('user/login.html', form=form)


# @app.route('/register/', methods=['GET', 'POST'])
# def register():
#     form = RegisterForm()

#     if form.validate_on_submit():
#         salt = str(uuid.uuid4())
#         password_hash = hashlib.pbkdf2_hmac(
#             'sha256', form.password.data.encode('UTF-8'), salt.encode('UTF-8'), 1000)

#         user = User(
#             username=form.username.data,
#             first_name=form.first_name.data,
#             family_name=form.family_name.data,
#             email=form.email.data,
#             password_salt=salt,
#             password_hash=password_hash,
#         )

#         db_session.add(user)
#         db_session.commit()

#         create_session(user.id)

#         flask.flash('Du hast dich erfolgreich registriert.', 'info')

#         return flask.redirect(flask.url_for('account'))

#     return flask.render_template('user/register.html', form=form)


# @app.route('/logout/')
# def logout():
#     close_session()
#     return flask.redirect(flask.url_for('index'))
