import smtplib

import pytz
from datetime import datetime
from flask import Blueprint, current_app, flash, request, url_for, render_template, redirect
from .security import manager_required
from .models import Event, User, GroupMember, GroupEventRelation, Group, Participant, db
from .forms import EventMailForm
from .utils import now

import os
import time
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

bp = Blueprint("mail", __name__, url_prefix="/mail")


def send_single_mail(recipient, subject, text, html=None):
    assert isinstance(recipient, str), recipient
    assert isinstance(subject, str), subject
    assert isinstance(text, str), text

    sender = current_app.config['HOST_MAIL_ADDRESS']

    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(text, 'plain'))

    if html is not None:
        msg.attach(MIMEText(html, 'html'))

    current_app.logger.info(f'Send email to {recipient}, subject="{subject}", sender={sender}')

    timer = time.time()
    stdout, stderr = None, None
    try:
        p = subprocess.Popen(['sendmail', "-t", "-oi"], stdin=subprocess.PIPE)
        stdout, stderr = p.communicate(input=msg.as_bytes(), timeout=10)
    # TODO NameError: name 'TimeoutExpired' is not defined
    except TimeoutExpired:
        p.kill()
        stdout, stderr = p.communicate()
    except Exception:
        current_app.logger.exception('failed to invoke sendmail command')

    current_app.logger.info(
        f'sendmail command completed (elapsed: {time.time() - timer:.3f}): '
        f'returncode={p.returncode}, stdout={stdout}, stderr={stderr}')

@bp.route('/group/<int:id>/info', methods=['GET', 'POST'])
@manager_required
def group_info(id):
    return 'Group info'

@bp.route('/event/<int:id>/invite', methods=['GET', 'POST'])
@manager_required
def event_invite(id):
    event = Event.query.get_or_404(id)

    users = User.query.\
        join(GroupMember, GroupMember.user_id == User.id).\
        join(Group, Group.id == GroupMember.group_id).\
        join(GroupEventRelation, GroupEventRelation.group_id == Group.id).\
        join(Event, Event.id == GroupEventRelation.event_id).\
        outerjoin(Participant, Participant.event_id == Event.id).\
        filter(Event.id == id).\
        filter(Participant.id == None).\
        order_by(User.username).\
        all()

    form = EventMailForm()

    if form.validate_on_submit():

        invitations = []
        for user in users:
            token = os.urandom(16).hex()
            invitations.append(Participant(
                user=user,
                event=event,
                token=token,
                registration_status=Participant.RegistrationStatus.INVITED
            ))

        event.registration_start = now
        db.session.commit()

        for inv in invitations:
            token_url = url_for('participant.edit', id=inv.id, token=inv.token, _external=True)
            send_single_mail(
                recipient=inv.user.email,
                subject=inv.event.name,
                text=render_template(
                    'mail/invitation.text',
                    invitation=inv, token_url=token_url),
                html=render_template(
                    'mail/invitation.html',
                    invitation=inv, token_url=token_url),
            )

        flash(f'Einladungen an {len(invitations)} Benutzer verschickt.', 'success')

        return redirect(url_for('participant.list', id=event.id))

    return render_template(
        'mail/invite.html',
        users=users,
        event=event,
        form=form
    )

@bp.route('/event/<int:id>/update', methods=['GET', 'POST'])
@manager_required
def event_update(id):
    event = Event.query.get_or_404(id)

    form = EventMailForm()

    if form.validate_on_submit():
        annotation = form.annotation.data
        for inv in event.participants:
            token_url = url_for('participant.edit', id=inv.id, token=inv.token, _external=True)
            send_single_mail(
                recipient=inv.user.email,
                subject=inv.event.name,
                text=render_template(
                    'mail/update.text',
                    invitation=inv, token_url=token_url, note=annotation),
                html=render_template(
                    'mail/udpate.html',
                    invitation=inv, token_url=token_url, note=annotation),
            )

        flash(f'Update an {len(invitations)} Teilnehmer verschickt.', 'success')

        return redirect(url_for('participant.list', id=event.id))

    return render_template(
        'mail/update.html',
        event=event,
        form=form
    )
