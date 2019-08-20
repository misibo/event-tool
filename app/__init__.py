import flask
from flask import request, url_for, render_template, current_app
from .forms import EditUserForm
from .models import db_session, User, Invitation, Event, Group
from . import auth
from . import mailing
from .utils import pretty_format_date
from datetime import datetime
import os
from flask_mail import Mail
import sqlalchemy.event
import textwrap
from . import auth, group, event, invitation
import pytz

app = flask.Flask(__name__, instance_relative_config=True)
app.config.from_object('config')  # load ./config.py
app.config.from_pyfile('config.py')  # load ./instance/config.py
app.secret_key = b'misibo'  # os.urandom(16)
app.mail = Mail(app)
app.register_blueprint(auth.bp)
app.register_blueprint(group.bp)
app.register_blueprint(event.bp)
app.register_blueprint(invitation.bp)

app.add_template_global(pretty_format_date, 'pretty_format_date')


def send_invitations():
    pending = invitation.list_missing_invitations()
    current_app.logger.info(f'Check for pending invitations: {len(pending)} found')

    for inv in pending:
        token_url = request.url_root + url_for('invitation.edit', id=inv.id, token=inv.token)[1:]

        success = mailing.send_single_mail(
            recipient=inv.user.email,
            subject=inv.event.name,
            text=render_template(
                'mail/invitation.text',
                invitation=inv, token_url=token_url),
            html=render_template(
                'mail/invitation.html',
                invitation=inv, token_url=token_url),
        )

        inv.send_email_attempt_utc = pytz.utc.localize(datetime.utcnow())
        if success:
            inv.send_email_success_utc = pytz.utc.localize(datetime.utcnow())

        db_session.add(inv)

        # commit invitations to database individually,
        # in order to not affect subsequent invitations if something goes wrong
        db_session.commit()


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
        db_session.commit()

        flask.flash('Profil erfolgreich angepasst.')

    return flask.render_template('user/edit.html', form=form)
