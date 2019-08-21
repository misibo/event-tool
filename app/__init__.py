import pytz
from flask import current_app, Flask, render_template, request, url_for
from .utils import pretty_format_date
from flask_mail import Mail
from . import mailing
from datetime import datetime
from .models import db
from . import security, user, group, event, invitation

app = Flask(__name__, instance_relative_config=True)

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

app.add_template_global(pretty_format_date, 'pretty_format_date')

# register blueprints
app.register_blueprint(security.bp)
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

        db.add(inv)

        # commit invitations to database individually,
        # in order to not affect subsequent invitations if something goes wrong
        db.commit()

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('home.html')
