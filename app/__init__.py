import os
import hashlib
import uuid
import flask
import datetime
from .forms import RegisterForm, LoginForm, EditUserForm
from .models import User, db_session

app = flask.Flask(__name__)
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

from . import auth, group, event
app.register_blueprint(auth.bp)
app.register_blueprint(group.bp)
app.register_blueprint(event.bp)


@app.route('/', methods=['GET', 'POST'])
def index():
    return flask.render_template('home.html')


@app.route('/account/', methods=['GET', 'POST'])
@auth.login_required
def account():
    user = flask.g.user
    form = EditUserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.first_name = form.first_name.data
        user.email = form.email.data
        user.family_name = form.family_name.data
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
