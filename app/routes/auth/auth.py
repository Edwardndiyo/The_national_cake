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
import random
import re
from datetime import datetime, timedelta


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/auth/firebase", methods=["POST"])
def firebase_login():
    """
    Firebase login
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            id_token:
              type: string
              description: Firebase ID token
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            message:
              type: string
            user:
              type: object
              properties:
                id: integer
                email: string
                fullname: string
                provider: string
      400:
        description: Missing Firebase ID token
      401:
        description: Invalid Firebase token
    """

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


# @auth_bp.route("/signup", methods=["POST"])
# def signup():
#     """
#     User signup
#     ---
#     tags:
#       - Auth
#     parameters:
#       - in: body
#         name: body
#         required: true
#         schema:
#           type: object
#           required:
#             - firstname
#             - lastname
#             - email
#             - phone
#             - nationality
#             - password
#           properties:
#             firstname: {type: string}
#             lastname: {type: string}
#             email: {type: string}
#             phone: {type: string}
#             nationality: {type: string}
#             referral: {type: string}
#             password: {type: string}
#             username: {type: string}
#     responses:
#       201:
#         description: Signup successful
#       400:
#         description: Email or phone already registered
#     """

#     data = request.get_json()

#     # Required fields
#     firstname = data.get("firstname")
#     lastname = data.get("lastname")
#     email = data.get("email")
#     phone = data.get("phone")
#     nationality = data.get("nationality")
#     referral = data.get("referral")  # optional
#     password = data.get("password")
#     username = data.get("username")

#     # Check existing users
#     if User.query.filter_by(email=email).first():
#         return jsonify({"error": "Email already registered"}), 400
#     if User.query.filter_by(phone=phone).first():
#         return jsonify({"error": "Phone already registered"}), 400

#     # Generate a username if not provided
#     if not username:
#         base_username = re.sub(
#             r"\W+", "", (firstname + lastname).lower()
#         )  # remove spaces/special chars
#         username = base_username
#         counter = 1
#         while User.query.filter_by(username=username).first():
#             username = f"{base_username}{counter}"
#             counter += 1
#     else:
#         # If provided, make sure it's unique
#         if User.query.filter_by(username=username).first():
#             return jsonify({"error": "Username already taken"}), 400

#     verification_token = str(uuid.uuid4())

#     user = User(
#         firstname=firstname,
#         lastname=lastname,
#         fullname=f"{firstname} {lastname}",
#         username=username,
#         email=email,
#         phone=phone,
#         nationality=nationality,
#         referral=referral,
#         password_hash=hash_password(password),
#         provider="local",
#         is_verified=False,
#         verification_token=verification_token,
#     )
#     db.session.add(user)
#     db.session.commit()

#     # Send verification email (prints in console for now)
#     verify_url = f"https:api.nationalcake.ng/auth/verify/{verification_token}"
#     # send_email(
#     #     "Verify your email",
#     #     user.email,
#     #     f"Hi {user.firstname}, click the link to verify your account: {verify_url}",
#     # )

#     # generate verification token & send mail
#     token = generate_verification_token(user.email)
#     send_verification_email(user, token)

#     return (
#         jsonify(
#             {
#                 "message": "Signup successful, please verify your email!",
#                 "username": user.username,
#             }
#         ),
#         201,
#     )

# ---------------------------
# SIGNUP
# ---------------------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    """
    User signup with OTP email verification
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - firstname
            - lastname
            - email
            - phone
            - nationality
            - password
          properties:
            firstname: {type: string}
            lastname: {type: string}
            email: {type: string}
            phone: {type: string}
            nationality: {type: string}
            referral: {type: string}
            password: {type: string}
            username: {type: string}
    responses:
      201:
        description: Signup successful, OTP sent
      400:
        description: Email or phone already registered
    """

    data = request.get_json()
    firstname = data.get("firstname")
    lastname = data.get("lastname")
    email = data.get("email")
    phone = data.get("phone")
    nationality = data.get("nationality")
    referral = data.get("referral")
    password = data.get("password")
    username = data.get("username")

    # Check uniqueness
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400
    if User.query.filter_by(phone=phone).first():
        return jsonify({"error": "Phone already registered"}), 400

    # Generate unique username if not provided
    if not username:
        base_username = re.sub(r"\W+", "", (firstname + lastname).lower())
        username = base_username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
    else:
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already taken"}), 400

    # Create user (not verified yet)
    user = User(
        firstname=firstname,
        lastname=lastname,
        fullname=f"{firstname} {lastname}",
        username=username,
        email=email,
        phone=phone,
        nationality=nationality,
        referral=referral,
        password_hash=hash_password(password),
        provider="local",
        is_verified=False,
    )
    db.session.add(user)
    db.session.commit()

    # Generate OTP (6-digit)
    otp_code = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=10)

    # otp_entry = PasswordResetOTP(
    #     user_id=user.id,
    #     otp=otp_code,
    #     expires_at=expiry,
    #     purpose="email_verification",  # new purpose flag
    # )
    otp_entry = PasswordResetOTP(
        user_id=user.id,
        # email=user.email,   # <-- FIX
        otp=otp_code,
        expires_at=expiry,
        purpose="email_verification",
    )

    db.session.add(otp_entry)
    db.session.commit()

    # Send OTP via email
    send_email(
        "Verify your email",
        user.email,
        f"Hi {user.firstname},\n\nYour verification code is: {otp_code}\n\nIt will expire in 10 minutes.",
    )

    return jsonify({
        "message": "Signup successful, please verify your email with the OTP code!",
        "username": user.username,
    }), 201

# ---------------------------
# VERIFY OTP
# ---------------------------
@auth_bp.route("/verify-signup-otp", methods=["POST"])
def verify_email_otp():
    """
    Verify email using OTP
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - otp
          properties:
            email: {type: string}
            otp: {type: string}
    responses:
      200:
        description: Email verified successfully
      400:
        description: Invalid or expired OTP
    """

    data = request.get_json()
    email = data.get("email")
    otp_code = data.get("otp")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    otp_entry = PasswordResetOTP.query.filter_by(
        user_id=user.id, otp=otp_code, purpose="email_verification"
    ).first()

    if not otp_entry:
        return jsonify({"error": "Invalid OTP"}), 400

    if otp_entry.expires_at < datetime.utcnow():
        return jsonify({"error": "OTP expired"}), 400

    # Mark user verified
    user.is_verified = True
    db.session.delete(otp_entry)
    db.session.commit()

    return jsonify({"message": "Email verified successfully!"}), 200
  

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
    """
    Verify email
    ---
    tags:
      - Auth
    parameters:
      - in: path
        name: token
        type: string
        required: true
        description: Verification token
    responses:
      200:
        description: Email verified successfully
      400:
        description: Invalid or expired verification link
    """

    user = User.query.filter_by(verification_token=token).first()
    if not user:
        return jsonify({"error": "Invalid or expired verification link"}), 400

    user.is_verified = True
    user.verification_token = None
    db.session.commit()

    return jsonify({"message": "Email verified successfully"}), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    User login
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - fullname
            - password
          properties:
            fullname: {type: string}
            password: {type: string}
    responses:
      200:
        description: Login successful
        schema:
          type: object
          properties:
            access_token: {type: string}
            refresh_token: {type: string}
      401:
        description: Invalid credentials
      403:
        description: Please verify your email first
    """

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
    """
    Refresh JWT tokens
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: New access and refresh tokens
        schema:
          type: object
          properties:
            access_token: {type: string}
            refresh_token: {type: string}
    """

    user_id = get_jwt_identity()
    new_access_token = create_access_token(identity=user_id)
    new_refresh_token = create_refresh_token(identity=user_id)

    return (
        jsonify({"access_token": new_access_token, "refresh_token": new_refresh_token}),
        200,
    )


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Request password reset OTP
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [email]
          properties:
            email: {type: string}
    responses:
      200:
        description: OTP sent to email
      404:
        description: Email not found
      429:
        description: Too many requests
    """

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
    """
    Verify password reset OTP
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [email, otp]
          properties:
            email: {type: string}
            otp: {type: string}
    responses:
      200:
        description: OTP verified successfully
      400:
        description: Invalid or expired OTP
    """

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
    """
    Reset password
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [email, new_password, confirm_password]
          properties:
            email: {type: string}
            new_password: {type: string}
            confirm_password: {type: string}
    responses:
      200:
        description: Password reset successful
      400:
        description: Invalid input or OTP not verified
      404:
        description: User not found
    """

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
