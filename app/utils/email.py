# app/utils/email.py
import os
import resend
from flask import current_app


def send_email(subject: str, to_email: str, body: str, from_email: str = None):
    """
    Send email via Resend API (v0.9+).
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        current_app.logger.warning("RESEND_API_KEY missing — email skipped")
        return False

    resend.api_key = api_key

    sender = from_email or os.getenv("MAIL_DEFAULT_SENDER", "onboarding@resend.dev")

    try:
        response = resend.Emails.send(
            from_=sender,  # ← CHANGE THIS TO: from=sender
            to=[to_email],
            subject=subject,
            text=body,
        )

        # Log full response for debugging
        current_app.logger.info(f"Resend response: {response}")

        if response and response.get("id"):
            current_app.logger.info(f"Email queued: {response['id']} → {to_email}")
            return True
        else:
            current_app.logger.error(f"Resend failed (no ID): {response}")
            return False

    except Exception as e:
        current_app.logger.error(f"Email exception: {str(e)}")
        return False


# import smtplib
# from email.mime.text import MIMEText
# from flask import current_app


# def send_email(subject, recipient, body):
#     app = current_app
#     msg = MIMEText(body)
#     msg["Subject"] = subject
#     msg["From"] = app.config["MAIL_DEFAULT_SENDER"]
#     msg["To"] = recipient

#     try:
#         with smtplib.SMTP(
#             app.config["MAIL_SERVER"], app.config["MAIL_PORT"]
#         ) as server:
#             server.starttls()
#             server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
#             server.send_message(msg)
#         print("✅ Email sent successfully")
#     except Exception as e:
#         print("❌ Email send failed:", e)
#         raise


# import smtplib
# import ssl
# import certifi
# from email.mime.text import MIMEText
# from flask import current_app


# def send_email(subject, recipient, body):
#     import socket

#     app = current_app

#     msg = MIMEText(body)
#     msg["Subject"] = subject
#     msg["From"] = app.config["MAIL_DEFAULT_SENDER"]
#     msg["To"] = recipient

#     context = ssl.create_default_context(cafile=certifi.where())

#     try:
#         print(
#             f"Connecting to SMTP server {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}..."
#         )
#         with smtplib.SMTP_SSL(
#             app.config["MAIL_SERVER"],
#             app.config["MAIL_PORT"],
#             context=context,
#             timeout=15,  # 👈 add timeout
#         ) as server:
#             print("Connected to mail server successfully.")
#             server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
#             server.send_message(msg)
#             print("Email sent successfully!")
#     except (smtplib.SMTPException, socket.error) as e:
#         print("Email send failed:", e)
#         raise


# def send_email(subject, recipient, body):
#     """
#     Securely sends an email using the Flask app's MAIL_* config,
#     but with an explicit certifi-based SSL context to prevent
#     certificate verification failures on macOS.
#     """

#     app = current_app

#     msg = MIMEText(body)
#     msg["Subject"] = subject
#     msg["From"] = app.config["MAIL_DEFAULT_SENDER"]
#     msg["To"] = recipient

#     context = ssl.create_default_context(cafile=certifi.where())

#     try:
#         # open secure SMTP connection manually
#         with smtplib.SMTP_SSL(
#             app.config["MAIL_SERVER"],
#             app.config["MAIL_PORT"],
#             context=context,
#         ) as server:
#             server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
#             server.send_message(msg)
#     except Exception as e:
#         print("Email send failed:", e)
#         raise


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
