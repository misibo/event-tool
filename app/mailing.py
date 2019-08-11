from flask_mail import Message
import app as main


def send_single_mail(recipient, subject, text):
    msg = Message(
        subject,
        sender="root@localhost",
        recipients=[recipient])

    msg.body = text

    try:
        main.mail.send(msg)
    except Exception:
        return False
    else:
        return True
