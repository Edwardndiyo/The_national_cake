# app/profile/routes.py
import os
import time
from werkzeug.utils import secure_filename
from flask import Blueprint, request, current_app
from app import db
from app.models import User
from app.utils.decorators import token_required, roles_required
from app.utils.responses import success_response, error_response

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")

# Allowed profile update fields
ALLOWED_UPDATE_FIELDS = {
    "firstname",
    "lastname",
    "username",
    "nationality",
    "avatar",
    "phone",
    "referral",
}


def user_to_dict(user):
    return {
        "id": user.id,
        "firstname": user.firstname,
        "lastname": user.lastname,
        "fullname": user.fullname,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "nationality": user.nationality,
        "avatar": user.avatar,
        "home_era": user.home_era,
        "role": user.role,
        "points": user.points,
        "is_verified": bool(user.is_verified),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


# ---------------------------
# GET CURRENT USER PROFILE
# ---------------------------
@profile_bp.route("/me", methods=["GET"])
@token_required
def get_my_profile(current_user):
    """
    Get current user profile
    ---
    tags:
      - Profile
    responses:
      200:
        description: Profile fetched successfully
    """
    """Return profile for authenticated user."""
    return success_response(user_to_dict(current_user), "Profile fetched successfully")


# ---------------------------
# GET PROFILE (by id or username) - Public
# ---------------------------
@profile_bp.route("/<identifier>", methods=["GET"])
def get_profile(identifier):
    """
    Get user profile (by ID or username)
    ---
    tags:
      - Profile
    parameters:
      - in: path
        name: identifier
        required: true
        type: string
        description: User ID (int) or username (string)
    responses:
      200:
        description: Profile fetched successfully
      404:
        description: User not found
    """
    """Fetch a user profile by ID or username (public)."""
    user = None
    if identifier.isdigit():
        user = User.query.get(int(identifier))
    else:
        user = User.query.filter_by(username=identifier).first()

    if not user:
        return error_response("User not found", 404)

    return success_response(user_to_dict(user), "Profile fetched successfully")


# ---------------------------
# UPDATE PROFILE (authenticated user)
# ---------------------------
@profile_bp.route("/update", methods=["PUT"])
@token_required
def update_profile(current_user):
    """
    Update profile (authenticated user)
    ---
    tags:
      - Profile
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            firstname: {type: string}
            lastname: {type: string}
            username: {type: string}
            nationality: {type: string}
            avatar: {type: string}
            phone: {type: string}
            referral: {type: string}
    responses:
      200:
        description: Profile updated successfully
      400:
        description: Invalid input or uniqueness constraint failed
    """
    """
    Update the current user's profile.
    Allowed fields: firstname, lastname, username, nationality, avatar, phone, referral.
    """
    data = request.get_json() or {}

    # username uniqueness check (if changing)
    if "username" in data and data["username"] != current_user.username:
        if User.query.filter_by(username=data["username"]).first():
            return error_response("Username already taken", 400)

    # phone uniqueness check (if changing)
    if "phone" in data and data["phone"] != current_user.phone:
        if User.query.filter_by(phone=data["phone"]).first():
            return error_response("Phone already registered", 400)

    updated = False
    for field, value in data.items():
        if field in ALLOWED_UPDATE_FIELDS:
            setattr(current_user, field, value)
            updated = True

    # always update fullname if names changed
    if ("firstname" in data or "lastname" in data) and (
        current_user.firstname and current_user.lastname
    ):
        current_user.fullname = f"{current_user.firstname} {current_user.lastname}"

    if updated:
        db.session.commit()
        return success_response(
            user_to_dict(current_user), "Profile updated successfully"
        )
    else:
        return error_response("No valid fields to update", 400)


# ---------------------------
# UPLOAD AVATAR (multipart/form-data)
# ---------------------------
@profile_bp.route("/avatar", methods=["POST"])
@token_required
def upload_avatar(current_user):
    """
    Upload avatar image
    ---
    tags:
      - Profile
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: avatar
        type: file
        required: true
        description: Avatar image file
    responses:
      201:
        description: Avatar uploaded successfully
      400:
        description: Invalid or missing file
    """
    """
    Upload avatar image for the authenticated user.
    - Accepts multipart/form-data with key 'avatar'.
    - Saves to: <app.static_folder>/uploads/avatars/<filename>
    - Returns public URL path to the avatar (e.g. /static/uploads/avatars/<filename>)
    NOTE: this is local storage; for production switch to S3 and update returned URL.
    """
    if "avatar" not in request.files:
        return error_response("No avatar file provided", 400)

    file = request.files["avatar"]
    if file.filename == "":
        return error_response("Empty filename", 400)

    filename = secure_filename(file.filename)
    timestamp = int(time.time())
    filename = f"{current_user.id}_{timestamp}_{filename}"

    uploads_dir = os.path.join(current_app.static_folder, "uploads", "avatars")
    os.makedirs(uploads_dir, exist_ok=True)

    file_path = os.path.join(uploads_dir, filename)
    file.save(file_path)

    # Build a URL that the frontend can access (Flask static url path)
    avatar_url = f"{current_app.static_url_path}/uploads/avatars/{filename}"

    # Save to user
    current_user.avatar = avatar_url
    db.session.commit()

    return success_response({"avatar": avatar_url}, "Avatar uploaded successfully", 201)


# ---------------------------
# SET HOME ERA (authenticated user)
# ---------------------------
@profile_bp.route("/home-era", methods=["POST"])
@token_required
def set_home_era(current_user):
    """
    Set home era
    ---
    tags:
      - Profile
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [home_era]
          properties:
            home_era: {type: string}
    responses:
      200:
        description: Home era updated successfully
      400:
        description: home_era is required
    """
    """
    Set the user's home era choice.
    Body: { "home_era": "Renaissance" }
    """
    data = request.get_json() or {}
    era = data.get("home_era")
    if not era:
        return error_response("home_era is required", 400)

    current_user.home_era = era
    db.session.commit()
    return success_response({"home_era": current_user.home_era}, "Home era updated")


# ---------------------------
# LEADERBOARD (public)
# ---------------------------
@profile_bp.route("/leaderboard", methods=["GET"])
def leaderboard():
    """
    Get leaderboard (public)
    ---
    tags:
      - Profile
    parameters:
      - in: query
        name: limit
        type: integer
        required: false
        default: 10
        description: Number of top users to return
    responses:
      200:
        description: Leaderboard fetched successfully
    """
    """
    Return top users by points.
    Query params:
      - limit (optional, default=10)
    """
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        limit = 10
    users = User.query.order_by(User.points.desc()).limit(limit).all()
    data = [
        {
            "id": u.id,
            "username": u.username,
            "fullname": u.fullname,
            "points": u.points,
            "avatar": u.avatar,
        }
        for u in users
    ]
    return success_response(data, "Leaderboard fetched successfully")


# ---------------------------
# ADMIN: CHANGE ROLE
# ---------------------------
@profile_bp.route("/<int:user_id>/role", methods=["PUT"])
@token_required
@roles_required("admin")
def change_role(current_user, user_id):
    """
    Change user role (Admin only)
    ---
    tags:
      - Profile (Admin)
    parameters:
      - in: path
        name: user_id
        required: true
        type: integer
      - in: body
        name: body
        schema:
          type: object
          required: [role]
          properties:
            role:
              type: string
              enum: [user, moderator, admin]
    responses:
      200:
        description: User role updated
      400:
        description: Invalid role
      404:
        description: User not found
    """
    """
    Admin-only: change a user's role.
    Body: { "role": "moderator" }  # allowed: user, moderator, admin
    """
    data = request.get_json() or {}
    new_role = data.get("role")
    if new_role not in ("user", "moderator", "admin"):
        return error_response("Invalid role", 400)

    user = User.query.get(user_id)
    if not user:
        return error_response("User not found", 404)

    user.role = new_role
    db.session.commit()
    return success_response({"id": user.id, "role": user.role}, "User role updated")


# ---------------------------
# ADMIN: VERIFY USER
# ---------------------------
@profile_bp.route("/<int:user_id>/verify", methods=["PUT"])
@token_required
@roles_required("admin")
def verify_user(current_user, user_id):
    """
    Verify user (Admin only)
    ---
    tags:
      - Profile (Admin)
    parameters:
      - in: path
        name: user_id
        required: true
        type: integer
    responses:
      200:
        description: User marked as verified
      404:
        description: User not found
    """
    """
    Admin-only: mark user as verified (is_verified=True)
    """
    user = User.query.get(user_id)
    if not user:
        return error_response("User not found", 404)

    user.is_verified = True
    db.session.commit()
    return success_response(
        {"id": user.id, "is_verified": True}, "User marked as verified"
    )
