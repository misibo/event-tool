import smtplib

import pytz
import datetime
from flask import current_app, request, url_for, render_template
from flask_mail import Message
from . import mailing, invitation


def send_single_mail(recipient, subject, text, html=None):
    assert isinstance(recipient, str), recipient
    assert isinstance(subject, str), subject
    assert isinstance(text, str), text

    sender = current_app.config['HOST_MAIL_ADDRESS']
    msg = Message(
        subject,
        sender=sender,
        recipients=[recipient])

    msg.body = text
    if html is not None:
        msg.html = html

    current_app.logger.info(f'Send email to {recipient}, subject="{subject}", sender={sender}')
    try:
        current_app.mail.send(msg)
    except smtplib.SMTPException:
        current_app.logger.exception(f'Could not send email')
        return False
    else:
        return True


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
