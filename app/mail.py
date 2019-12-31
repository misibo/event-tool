import smtplib

import pytz
from datetime import datetime
from flask import Blueprint, current_app, flash, request, url_for, render_template, redirect
from sqlalchemy.orm import joinedload, subqueryload
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

@bp.route('/event/<int:id>/info', methods=['GET', 'POST'])
@manager_required
def event_info(id):
    event = Event.query.\
        options(joinedload(Event.groups)).\
        options(joinedload(Event.participants).joinedload(Participant.user)).\
        get_or_404(id)

    members = GroupMember.query.\
        options(joinedload(GroupMember.user)).\
        join(User, User.id == GroupMember.user_id).\
        join(GroupEventRelation, GroupEventRelation.group_id == GroupMember.group_id).\
        outerjoin(Participant, Participant.event_id == GroupEventRelation.event_id).\
        filter(GroupEventRelation.event_id == id).\
        filter(Participant.id == None).\
        all()

    spectators = []
    uninvited = []

    for member in members:
        if member.role == GroupMember.Role.SPECTATOR:
            spectators.append(member.user)
        else:
            uninvited.append(member.user)

    form = EventMailForm(event_details=event.details)

    if form.validate_on_submit():

        event.details = form.data.event_details

        if not event.is_registration_allowed():
            event.registration_start = now

        for user in uninvited:
            event.participants.append(Participant(
                registration_status=Participant.RegistrationStatus.INVITED,
                token=os.urandom(16).hex(),
                user=user
            ))

        db.session.commit()

        for participant in event.participants:
            send_single_mail(
                recipient=participant.user.email,
                subject=event.name,
                text=render_template('mail/msg/event_info.text', user=participant.user, event=event, annotation=form.data.annotation, participant=participant),
                html=render_template('mail/msg/event_info.html', user=participant.user, event=event, annotation=form.data.annotation, participant=participant)
            )

        for user in spectators:
            send_single_mail(
                recipient=user.username,
                subject=event.name,
                text=render_template('mail/msg/event_info.text', user=user, event=event, annotation=form.data.annotation),
                html=render_template('mail/msg/event_info.html', user=user, event=event, annotation=form.data.annotation)
            )

        flash(f'{len(event.participants)} Mitglieder und {len(spectators)} Zuschauer wurde ein Mail gesendet.', 'success')

        return redirect(url_for('participant.list', id=event.id))

    return render_template(
        'mail/event_info.html',
        spectators=spectators,
        uninvited=uninvited,
        participants=event.participants,
        event=event,
        form=form
    )
