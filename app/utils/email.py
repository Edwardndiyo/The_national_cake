from flask_mailman import EmailMessage
from flask import current_app


def send_email(subject, recipient, body):
    msg = EmailMessage(
        subject,
        body,
        current_app.config["MAIL_DEFAULT_SENDER"],
        [recipient],
    )
    msg.send()
