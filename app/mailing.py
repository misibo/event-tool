from flask import current_app
from flask_mail import Message


def send_single_mail(recipient, subject, text, html=None):
    assert isinstance(recipient, str), recipient
    assert isinstance(subject, str), subject
    assert isinstance(text, str), text

    msg = Message(
        subject,
        sender=current_app.config['HOST_MAIL_ADDRESS'],
        recipients=[recipient])

    msg.body = text
    if html is not None:
        msg.html = html

    try:
        current_app.mail.send(msg)
    except Exception:
        current_app.logger.exception(f'Could not delivery email to {recipient}')
        return False
    else:
        return True
