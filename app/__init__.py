from datetime import datetime

import os
import pytz
import itsdangerous
from flask import Flask, current_app, render_template, request, url_for, flash
from flask_mail import Mail

from . import event, group, invitation, mailing, security, user, dashboard
from .models import db, User
from .utils import pretty_format_date

app = Flask(__name__, instance_relative_config=True, static_url_path='/static')

# load conig
app.config.from_object('config')  # load ./config.py
app.config.from_pyfile('config.py')  # load ./instance/config.py
app.secret_key = os.urandom(16)  # os.urandom(16)
app.secure_serializer = itsdangerous.URLSafeSerializer(os.urandom(16))

# initizalize database
db.init_app(app)

# create tables
with app.app_context():
    db.create_all()

# set mailer
app.mail = Mail(app)

app.add_template_global(pretty_format_date, 'pretty_format_date')

# register blueprints
app.register_blueprint(security.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(user.bp)
app.register_blueprint(group.bp)
app.register_blueprint(event.bp)
app.register_blueprint(invitation.bp)


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

        db.session.add(inv)

        # commit invitations to database individually,
        # in order to not affect subsequent invitations if something goes wrong
        db.session.commit()


@app.template_filter()
def parse_freeform(text):
    """Convert a string to all caps."""
    return [x.strip() for x in text.split('\n') if x.strip() != '']


@app.context_processor
def inject_stage_and_region():
    return dict(
        UserRole=User.Role,
    )


@app.route('/', methods=['GET', 'POST'])
def index():
    flash('message', 'primary')
    flash('warning', 'warning')
    flash('error', 'danger')
    flash('info', 'success')
    flash('random', 'random')
    return render_template('home.html')
