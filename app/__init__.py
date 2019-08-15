import flask
from flask_mail import Mail
from .models import db
from . import security, user, group, event

app = flask.Flask(__name__, instance_relative_config=True)

# load conig
app.config.from_object('config')  # load ./config.py
app.config.from_pyfile('config.py')  # load ../instance/config.py

# initizalize database
db.init_app(app)

# create tables
with app.app_context():
    db.create_all()

# set mailer
app.mail = Mail(app)

# register blueprints
app.register_blueprint(security.bp)
app.register_blueprint(user.bp)
app.register_blueprint(group.bp)
app.register_blueprint(event.bp)


@app.route('/', methods=['GET', 'POST'])
def index():
    return flask.render_template('home.html')
