import smtplib

import pytz
from datetime import datetime
from flask import current_app, request, url_for, render_template
from . import invitation

import os
import time
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


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
    except TimeoutExpired:
        p.kill()
        stdout, stderr = p.communicate()
    except Exception:
        current_app.logger.exception('failed to invoke sendmail command')

    current_app.logger.info(
        f'sendmail command completed (elapsed: {time.time() - timer:.3f}): '
        f'returncode={p.returncode}, stdout={stdout}, stderr={stderr}')


def send_invitations():
    from .models import db

    pending = invitation.list_missing_invitations()
    current_app.logger.info(f'Check for pending invitations: {len(pending)} found')

    for inv in pending:
        db.session.add(inv)
        db.session.commit()

        assert inv.id is not None
        token_url = request.url_root + url_for('invitation.edit', id=inv.id, token=inv.token)[1:]

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

        inv.send_email_attempt_utc = pytz.utc.localize(datetime.utcnow())
        db.session.commit()
