from datetime import datetime

import logging
import os
import pytz
import itsdangerous
from flask import Flask, current_app, render_template, request, url_for, flash, redirect
from flask_mail import Mail
from flask_simplemde import SimpleMDE
from flaskext.markdown import Markdown
from werkzeug.exceptions import NotFound, Unauthorized, Forbidden, MethodNotAllowed
from . import utils
from logging.config import dictConfig
from urllib.parse import urlparse

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
Markdown(app)
SimpleMDE(app)

# load conig
app.config.from_object('config')  # load ./config.py
app.config.from_pyfile('config.py')  # load ./instance/config.py
app.secret_key = os.urandom(16)  # os.urandom(16)
app.secure_serializer = itsdangerous.URLSafeSerializer(os.urandom(16))

# set mailer
app.add_template_global(utils.pretty_format_date, 'pretty_format_date')


# register blueprints
from . import event, group, groupmember, participant, security, user, dashboard, mail
app.register_blueprint(security.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(user.bp)
app.register_blueprint(group.bp)
app.register_blueprint(groupmember.bp)
app.register_blueprint(event.bp)
app.register_blueprint(participant.bp)
app.register_blueprint(mail.bp)


# initizalize database
from .models import db
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

app.jinja_env.filters['utc_to_localtime'] = utils.utc_to_localtime
app.jinja_env.filters['localtime_to_utc'] = utils.localtime_to_utc
app.jinja_env.filters['shortdate'] = utils.shortdate
app.jinja_env.filters['longdate'] = utils.longdate
app.jinja_env.filters['shortdatetime'] = utils.shortdatetime
app.jinja_env.filters['longdatetime'] = utils.longdatetime

@app.context_processor
def utils_processor():

    def _merge_into(d, **kwargs):
        d.update(kwargs)
        return d

    return dict(
        merge_into=_merge_into,
        url_back=utils.url_back
    )


@app.context_processor
def timezone_processor():
    return dict(
        tz=pytz.timezone(app.config['TIMEZONE'])
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

