# app/utils/email.py
import os
from flask import current_app
from resend import Resend
from resend.exceptions import ResendException

# Global Resend client (lazy init)
_resend_client = None


def _get_resend_client():
    global _resend_client
    if _resend_client is None:
        api_key = os.getenv("RESEND_API_KEY")
        if not api_key:
            current_app.logger.warning("RESEND_API_KEY not set—emails will be skipped")
            _resend_client = None
        else:
            _resend_client = Resend(api_key=api_key)
    return _resend_client


def send_email(subject: str, to_email: str, body: str, from_email: str = None):
    """
    Send email via Resend API.

    Args:
        subject: Email subject
        to_email: Recipient email
        body: Plaintext body (or HTML if you add html=body)
        from_email: Optional sender (defaults to MAIL_DEFAULT_SENDER env var)

    Returns:
        bool: True if sent, False on failure (logs error, doesn't raise)

    Secure: Env vars only, no hard-codes. Fails gracefully.
    """
    client = _get_resend_client()
    if not client:
        current_app.logger.warning(f"Email skipped to {to_email} (no API key)")
        return False

    sender = from_email or os.getenv("MAIL_DEFAULT_SENDER", "no-reply@nationalcake.ng")

    try:
        response = client.emails.send(
            from_=sender,
            to=[to_email],
            subject=subject,
            text=body,  # Plaintext for your OTP style
            # html=body if you want HTML (e.g., for links)
        )
        if response.status_code in (200, 202):
            current_app.logger.info(f"Email sent successfully to {to_email}")
            return True
        else:
            current_app.logger.error(
                f"Resend API error: {response.status_code} - {response.body}"
            )
            return False
    except ResendException as e:
        current_app.logger.error(f"Resend send failed: {str(e)}")
        return False
    except Exception as e:
        current_app.logger.error(f"Unexpected email error: {str(e)}")
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
