from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from app.extensions import db
from app.models import User, PasswordResetOTP
from app.utils.security import hash_password, verify_password, generate_otp, otp_expiry
from app.utils.responses import error_response, success_response
from app.utils.firebase import verify_firebase_token
from app.utils.tokens import generate_verification_token, confirm_verification_token
from app.utils.mailer import send_verification_email
import uuid
from app.utils.email import send_email


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/auth/firebase", methods=["POST"])
def firebase_login():
    data = request.get_json()
    id_token = data.get("id_token")

    if not id_token:
        return jsonify({"error": "Missing Firebase ID token"}), 400

    decoded = verify_firebase_token(id_token)
    if not decoded:
        return jsonify({"error": "Invalid Firebase token"}), 401

    # Extract Firebase details
    firebase_uid = decoded["uid"]
    email = decoded.get("email")
    name = decoded.get("name", "")
    picture = decoded.get("picture", "")

    # Try to find existing user
    user = User.query.filter(
        (User.firebase_uid == firebase_uid) | (User.email == email)
    ).first()

    if not user:
        # Create new local user
        user = User(
            firstname=name.split(" ")[0] if name else "Firebase",
            lastname=" ".join(name.split(" ")[1:]) if len(name.split()) > 1 else "",
            fullname=name if name else "Firebase User",
            username=email.split("@")[0] if email else firebase_uid,
            email=email or f"{firebase_uid}@firebase.local",
            phone="",
            nationality="Unknown",
            password_hash=None,  # no local password
            avatar=picture,
            provider="firebase",
            firebase_uid=firebase_uid,
        )
        db.session.add(user)
        db.session.commit()

    # Return JWT or session token (reuse your local auth logic)
    return jsonify({
        "message": "Firebase login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "fullname": user.fullname,
            "provider": user.provider
        }
    })

@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()

    # Required fields
    firstname = data.get("firstname")
    lastname = data.get("lastname")
    email = data.get("email")
    phone = data.get("phone")
    nationality = data.get("nationality")
    referral = data.get("referral")  # optional
    password = data.get("password")

    # Check existing users
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
    if User.query.filter_by(phone=phone).first():
        return jsonify({"error": "Phone already registered"}), 400

    verification_token = str(uuid.uuid4())

    user = User(
        firstname=firstname,
        lastname=lastname,
        fullname=f"{firstname} {lastname}",
        email=email,
        phone=phone,
        nationality=nationality,
        referral=referral,
        password_hash=hash_password(password),
        provider="local",
        is_verified=False,
        verification_token=verification_token,
    )
    db.session.add(user)
    db.session.commit()

    # Send verification email (prints in console for now)
    verify_url = f"http://localhost:5000/auth/verify/{verification_token}"
    send_email(
        "Verify your email",
        user.email,
        f"Hi {user.firstname}, click the link to verify your account: {verify_url}",
    )

    # access_token = create_access_token(identity=str(user.id))
    # refresh_token = create_refresh_token(identity=str(user.id))
    # generate verification token & send mail
    token = generate_verification_token(user.email)
    send_verification_email(user, token)

    # return jsonify({"access_token": access_token, "refresh_token": refresh_token}), 201
    return jsonify({"message": "Signup successful, please verify your email!"}), 201


# @auth_bp.route("/verify-email", methods=["GET"])
# def verify_email():
#     token = request.args.get("token")
#     email = confirm_verification_token(token)
#     if not email:
#         return jsonify({"error": "Invalid or expired token"}), 400

#     user = User.query.filter_by(email=email).first_or_404()
#     if user.is_verified:
#         return jsonify({"message": "Account already verified!"}), 200

#     user.is_verified = True
#     db.session.commit()

#     return jsonify({"message": "Email verified successfully!"}), 200


@auth_bp.route("/verify/<token>", methods=["GET"])
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        return jsonify({"error": "Invalid or expired verification link"}), 400

    user.is_verified = True
    user.verification_token = None
    db.session.commit()

    return jsonify({"message": "Email verified successfully"}), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    fullname = data.get("fullname")
    password = data.get("password")

    user = User.query.filter_by(fullname=fullname).first()
    if not user or not verify_password(password, user.password_hash):
        return jsonify({"error": "Invalid credentials"}), 401
    
    if not user.is_verified:
        return jsonify({"error": "Please verify your email first"}), 403

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({"access_token": access_token, "refresh_token": refresh_token}), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=user_id)
    new_refresh_token = create_refresh_token(identity=user_id)

    return (
        jsonify({"access_token": new_access_token, "refresh_token": new_refresh_token}),
        200,
    )


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "Email not found"}), 404

    # Check existing OTP requests in last minute
    from datetime import datetime, timedelta

    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
    recent_requests = PasswordResetOTP.query.filter(
        PasswordResetOTP.email == email, PasswordResetOTP.created_at >= one_minute_ago
    ).count()

    if recent_requests >= 5:
        return jsonify({"message": "Too many requests, try again later"}), 429

    # Generate new OTP
    otp = generate_otp()
    reset_otp = PasswordResetOTP(
        email=email, otp=otp, expiry=otp_expiry(), request_count=recent_requests + 1
    )
    db.session.add(reset_otp)
    db.session.commit()

    # For now, print OTP in console
    print(f"🔑 OTP for {email}: {otp}")

    return jsonify({"message": "OTP sent to your email"}), 200


@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")

    if not email or not otp:
        return jsonify({"message": "Email and OTP are required"}), 400

    record = (
        PasswordResetOTP.query.filter_by(email=email, otp=otp)
        .order_by(PasswordResetOTP.created_at.desc())
        .first()
    )

    if not record:
        return jsonify({"message": "Invalid OTP"}), 400

    if record.is_expired():
        return jsonify({"message": "OTP expired"}), 400

    record.is_verified = True
    db.session.commit()

    return jsonify({"message": "OTP verified successfully"}), 200

from werkzeug.security import generate_password_hash


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not email or not new_password or not confirm_password:
        return jsonify({"message": "Email and passwords are required"}), 400

    if new_password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    # Check if there’s a verified OTP for this email
    record = (
        PasswordResetOTP.query.filter_by(email=email, is_verified=True)
        .order_by(PasswordResetOTP.created_at.desc())
        .first()
    )

    if not record:
        return jsonify({"message": "OTP not verified"}), 400

    if record.is_expired():
        return jsonify({"message": "OTP expired"}), 400

    # Reset password
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    user.password = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"message": "Password reset successful"}), 200

