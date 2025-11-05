from werkzeug.security import generate_password_hash, check_password_hash
import random
from datetime import datetime, timedelta
from app.models import PasswordResetOTP


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def generate_otp():
    return str(random.randint(100000, 999999))


def otp_expiry():
    return datetime.utcnow() + timedelta(minutes=5)


def can_resend_otp(
    user_id: int, purpose: str = "email_verification", cooldown_minutes: int = 5
):
    """
    Returns True if user can request a new OTP (respects cooldown)
    """
    cutoff = datetime.utcnow() - timedelta(minutes=cooldown_minutes)
    recent = PasswordResetOTP.query.filter(
        PasswordResetOTP.user_id == user_id,
        PasswordResetOTP.purpose == purpose,
        PasswordResetOTP.created_at >= cutoff,
    ).first()
    return recent is None
