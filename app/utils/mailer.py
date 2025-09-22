# app/utils/mailer.py
from flask_mail import Message
from app.extensions import mail


def send_verification_email(user, token):
    verify_url = f"http://localhost:5000/auth/verify-email?token={token}"
    msg = Message(
        subject="Verify your email",
        recipients=[user.email],
        body=f"Hi {user.firstname},\n\nPlease verify your email by clicking this link: {verify_url}\n\nThanks!",
    )
    mail.send(msg)
