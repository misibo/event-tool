import smtplib

from flask import current_app
from flask_mail import Message


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
