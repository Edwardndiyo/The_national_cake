import smtplib
import ssl
import certifi
from email.mime.text import MIMEText
from flask import current_app


def send_email(subject, recipient, body):
    """
    Securely sends an email using the Flask app's MAIL_* config,
    but with an explicit certifi-based SSL context to prevent
    certificate verification failures on macOS.
    """
    app = current_app

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = app.config["MAIL_DEFAULT_SENDER"]
    msg["To"] = recipient

    context = ssl.create_default_context(cafile=certifi.where())

    try:
        # open secure SMTP connection manually
        with smtplib.SMTP_SSL(
            app.config["MAIL_SERVER"],
            app.config["MAIL_PORT"],
            context=context,
        ) as server:
            server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
            server.send_message(msg)
    except Exception as e:
        print("Email send failed:", e)
        raise




# from flask_mailman import EmailMessage
# from flask import current_app


# def send_email(subject, recipient, body):
#     msg = EmailMessage(
#         subject,
#         body,
#         current_app.config["MAIL_DEFAULT_SENDER"],
#         [recipient],
#     )
#     msg.send()
