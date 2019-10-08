from datetime import datetime

import os
import pytz
import itsdangerous
import celery
from flask import Flask, current_app, render_template, request, url_for, flash, redirect
from flask_mail import Mail, Message

from . import utils

app = Flask(__name__, instance_relative_config=True, static_url_path='/static')

# load conig
app.config.from_object('config')  # load ./config.py
app.config.from_pyfile('config.py')  # load ./instance/config.py
app.secret_key = os.urandom(16)  # os.urandom(16)
app.secure_serializer = itsdangerous.URLSafeSerializer(os.urandom(16))

# set mailer
app.mail = Mail(app)

app.add_template_global(utils.pretty_format_date, 'pretty_format_date')


# initialize celery
taskqueue = celery.Celery(
    'mailer',
    backend=f'redis://localhost:{app.config["REDIS_PORT"]}/0',
    broker=f'redis://localhost:{app.config["REDIS_PORT"]}/0',
)
taskqueue.conf.broker_transport_options = {
    'visibility_timeout': 300,  # seconds
}

class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)

taskqueue.Task = ContextTask

from . import mailing  # register celery tasks


# register blueprints
from . import event, group, invitation, security, user, dashboard
app.register_blueprint(security.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(user.bp)
app.register_blueprint(group.bp)
app.register_blueprint(event.bp)
app.register_blueprint(invitation.bp)


# initizalize database
from .models import db, User, GroupMember
db.init_app(app)

with app.app_context():
    db.create_all()


@app.template_filter()
def parse_freeform(text):
    """Convert a string to all caps."""
    from .parser import parse_text
    return parse_text(text)


@app.context_processor
def inject_stage_and_region():
    return dict(
        UserRole=User.Role,
        SPECTATOR=GroupMember.Role.SPECTATOR,
        MEMBER=GroupMember.Role.MEMBER,
        USER=User.Role.USER,
        MANAGER=User.Role.MANAGER,
        ADMIN=User.Role.ADMIN
    )


@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('dashboard.index'))
