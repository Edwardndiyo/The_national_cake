from flask import Blueprint, request
from app import db, socketio
from app.models import Badge, UserBadge
from app.utils.decorators import token_required, roles_required
from app.utils.responses import success_response, error_response

badge_bp = Blueprint("badges", __name__, url_prefix="/badges")


# ---------------------------
# CREATE BADGE (Admin only)
# ---------------------------
@badge_bp.route("/", methods=["POST"])
@token_required
@roles_required("admin")
def create_badge(current_user):
    data = request.get_json()
    if not data.get("name") or not data.get("description"):
        return error_response("Name and description are required", 400)

    badge = Badge(name=data["name"], description=data["description"])
    db.session.add(badge)
    db.session.commit()

    # 🔴 Emit real-time badge creation
    socketio.emit(
        "badge_created",
        {"id": badge.id, "name": badge.name, "description": badge.description},
        broadcast=True,
    )

    return success_response(
        {"id": badge.id, "name": badge.name, "description": badge.description},
        "Badge created successfully",
        201,
    )


# ---------------------------
# LIST ALL BADGES
# ---------------------------
@badge_bp.route("/", methods=["GET"])
@token_required
def list_badges(current_user):
    badges = Badge.query.all()
    data = [{"id": b.id, "name": b.name, "description": b.description} for b in badges]
    return success_response(data, "Badges fetched successfully")


# ---------------------------
# ASSIGN BADGE TO USER (Admin only)
# ---------------------------
@badge_bp.route("/assign", methods=["POST"])
@token_required
@roles_required("admin")
def assign_badge(current_user):
    data = request.get_json()
    if not data.get("badge_id") or not data.get("user_id"):
        return error_response("badge_id and user_id are required", 400)

    # check if badge exists
    badge = Badge.query.get(data["badge_id"])
    if not badge:
        return error_response("Badge not found", 404)

    # prevent duplicate assignment
    existing = UserBadge.query.filter_by(
        badge_id=data["badge_id"], user_id=data["user_id"]
    ).first()
    if existing:
        return error_response("User already has this badge", 400)

    user_badge = UserBadge(badge_id=data["badge_id"], user_id=data["user_id"])
    db.session.add(user_badge)
    db.session.commit()

    # 🔴 Emit real-time badge assignment
    socketio.emit(
        "badge_assigned",
        {
            "user_id": user_badge.user_id,
            "badge_id": user_badge.badge_id,
        },
        broadcast=True,
    )

    return success_response(
        {"user_id": user_badge.user_id, "badge_id": user_badge.badge_id},
        "Badge assigned successfully",
        201,
    )


# ---------------------------
# GET USER BADGES
# ---------------------------
@badge_bp.route("/user/<int:user_id>", methods=["GET"])
@token_required
def get_user_badges(current_user, user_id):
    user_badges = UserBadge.query.filter_by(user_id=user_id).all()
    data = [
        {
            "badge_id": ub.badge_id,
            "badge_name": ub.badge.name,
            "badge_description": ub.badge.description,
            "assigned_at": ub.assigned_at.isoformat() if ub.assigned_at else None,
        }
        for ub in user_badges
    ]
    return success_response(data, "User badges fetched successfully")
