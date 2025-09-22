from werkzeug.security import generate_password_hash, check_password_hash
import random
from datetime import datetime, timedelta


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def generate_otp():
    return str(random.randint(100000, 999999))


def otp_expiry():
    return datetime.utcnow() + timedelta(minutes=5)
