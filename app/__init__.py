from datetime import datetime

import logging
import os
import pytz
import itsdangerous
from flask import Flask, current_app, render_template, request, url_for, flash, redirect
from flask_mail import Mail
from werkzeug.exceptions import NotFound, Unauthorized, Forbidden, MethodNotAllowed
from . import utils
from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '%(levelname)s|%(module)s|%(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__, instance_relative_config=True, static_url_path='/static')


# load conig
app.config.from_object('config')  # load ./config.py
app.config.from_pyfile('config.py')  # load ./instance/config.py
app.secret_key = os.urandom(16)  # os.urandom(16)
app.secure_serializer = itsdangerous.URLSafeSerializer(os.urandom(16))

# set mailer
app.add_template_global(utils.pretty_format_date, 'pretty_format_date')


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

@app.template_filter()
def if_not(value, string):
    if value:
        return value
    else:
        return string

@app.context_processor
def utility_processor():
    def merge_into(d, **kwargs):
        d.update(kwargs)
        return d
    return dict(merge_into=merge_into)


@app.context_processor
def inject_stage_and_region():
    return dict(
        tz=pytz.timezone('Europe/Zurich'),
        UserRole=User.Role,
        SPECTATOR=GroupMember.Role.SPECTATOR,
        MEMBER=GroupMember.Role.MEMBER,
        USER=User.Role.USER,
        MANAGER=User.Role.MANAGER,
        ADMIN=User.Role.ADMIN
    )


@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('dashboard.upcoming'))

@app.errorhandler(NotFound)
@app.errorhandler(Unauthorized)
@app.errorhandler(Forbidden)
@app.errorhandler(MethodNotAllowed)
def handle_exception(exception):
    return render_template('exception.html', exception=exception)

