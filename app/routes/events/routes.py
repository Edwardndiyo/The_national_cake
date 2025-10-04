from flask import Blueprint, request
from app import db
from app.models import (
    Event,
    Mission,
    RSVP,
    User,
    # MissionProgress,
    MissionParticipant,
)
from app.utils.decorators import token_required, roles_required
from app.utils.responses import success_response, error_response
from datetime import datetime

events_bp = Blueprint("events", __name__, url_prefix="/events")


# ---------------------------
# Helper serializers
# ---------------------------
def event_to_dict(event):
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "start_date": event.start_date.isoformat() if event.start_date else None,
        "end_date": event.end_date.isoformat() if event.end_date else None,
        "created_by": event.created_by,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def mission_to_dict(mission):
    return {
        "id": mission.id,
        "title": mission.title,
        "description": mission.description,
        "points": mission.points,
        "event_id": mission.event_id,
        "created_at": mission.created_at.isoformat() if mission.created_at else None,
    }


# ---------------------------
# EVENTS
# ---------------------------
@events_bp.route("/", methods=["GET"])
def list_events():
    """
    List all events
    ---
    tags:
      - Events
    responses:
      200:
        description: List of events fetched successfully
    """
    """List all events (public)."""
    events = Event.query.order_by(Event.start_date.asc()).all()
    return success_response(
        [event_to_dict(e) for e in events], "Events fetched successfully"
    )


@events_bp.route("/<int:event_id>", methods=["GET"])
def get_event(event_id):
    """
    Get a single event
    ---
    tags:
      - Events
    parameters:
      - in: path
        name: event_id
        required: true
        type: integer
    responses:
      200:
        description: Event fetched successfully
      404:
        description: Event not found
    """
    """Fetch single event (public)."""
    event = Event.query.get(event_id)
    if not event:
        return error_response("Event not found", 404)
    return success_response(event_to_dict(event), "Event fetched successfully")


@events_bp.route("/", methods=["POST"])
@token_required
@roles_required("admin")
def create_event(current_user):
    """
    Create a new event (Admin only)
    ---
    tags:
      - Events
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [title, start_date]
          properties:
            title: {type: string}
            description: {type: string}
            start_date: {type: string, format: date-time}
            end_date: {type: string, format: date-time}
    responses:
      201:
        description: Event created successfully
      400:
        description: Invalid input
    """
    """Admin-only: create a new event."""
    data = request.get_json() or {}
    if not data.get("title") or not data.get("start_date"):
        return error_response("title and start_date are required", 400)

    try:
        start_date = datetime.fromisoformat(data["start_date"])
        end_date = (
            datetime.fromisoformat(data["end_date"]) if data.get("end_date") else None
        )
    except Exception:
        return error_response("Invalid date format. Use ISO format.", 400)

    event = Event(
        title=data["title"],
        description=data.get("description"),
        start_date=start_date,
        end_date=end_date,
        created_by=current_user.id,
    )
    db.session.add(event)
    db.session.commit()
    return success_response(event_to_dict(event), "Event created successfully", 201)


@events_bp.route("/<int:event_id>", methods=["PUT"])
@token_required
@roles_required("admin")
def update_event(current_user, event_id):
    """
    Update an event (Admin only)
    ---
    tags:
      - Events
    parameters:
      - in: path
        name: event_id
        required: true
        type: integer
      - in: body
        name: body
        schema:
          type: object
          properties:
            title: {type: string}
            description: {type: string}
            start_date: {type: string, format: date-time}
            end_date: {type: string, format: date-time}
    responses:
      200:
        description: Event updated successfully
      404:
        description: Event not found
    """
    """Admin-only: update an event."""
    event = Event.query.get(event_id)
    if not event:
        return error_response("Event not found", 404)

    data = request.get_json() or {}
    if "title" in data:
        event.title = data["title"]
    if "description" in data:
        event.description = data["description"]
    if "start_date" in data:
        try:
            event.start_date = datetime.fromisoformat(data["start_date"])
        except Exception:
            return error_response("Invalid start_date format", 400)
    if "end_date" in data:
        try:
            event.end_date = datetime.fromisoformat(data["end_date"])
        except Exception:
            return error_response("Invalid end_date format", 400)

    db.session.commit()
    return success_response(event_to_dict(event), "Event updated successfully")


@events_bp.route("/<int:event_id>", methods=["DELETE"])
@token_required
@roles_required("admin")
def delete_event(current_user, event_id):
    """
    Delete an event (Admin only)
    ---
    tags:
      - Events
    parameters:
      - in: path
        name: event_id
        required: true
        type: integer
    responses:
      200:
        description: Event deleted successfully
      404:
        description: Event not found
    """
    """Admin-only: delete an event."""
    event = Event.query.get(event_id)
    if not event:
        return error_response("Event not found", 404)
    db.session.delete(event)
    db.session.commit()
    return success_response({}, "Event deleted successfully")


# ---------------------------
# Event participation
# ---------------------------
@events_bp.route("/<int:event_id>/join", methods=["POST"])
@token_required
def join_event(current_user, event_id):
    """
    Join an event
    ---
    tags:
      - Events
    parameters:
      - in: path
        name: event_id
        required: true
        type: integer
    responses:
      200:
        description: Joined event successfully
      404:
        description: Event not found
      400:
        description: Already joined this event
    """
    """Join an event."""
    event = Event.query.get(event_id)
    if not event:
        return error_response("Event not found", 404)

    if current_user in event.participants:
        return error_response("Already joined this event", 400)

    event.participants.append(current_user)
    db.session.commit()
    return success_response(
        {"event_id": event.id, "user_id": current_user.id},
        "Joined event successfully",
    )


@events_bp.route("/<int:event_id>/leave", methods=["POST"])
@token_required
def leave_event(current_user, event_id):
    """
    Leave an event
    ---
    tags:
      - Events
    parameters:
      - in: path
        name: event_id
        required: true
        type: integer
    responses:
      200:
        description: Left event successfully
      404:
        description: Event not found
      400:
        description: Not part of this event
    """
    """Leave an event."""
    event = Event.query.get(event_id)
    if not event:
        return error_response("Event not found", 404)

    if current_user not in event.participants:
        return error_response("You are not part of this event", 400)

    event.participants.remove(current_user)
    db.session.commit()
    return success_response(
        {"event_id": event.id, "user_id": current_user.id},
        "Left event successfully",
    )


@events_bp.route("/<int:event_id>/participants", methods=["GET"])
def list_event_participants(event_id):
    """
    List event participants
    ---
    tags:
      - Events
    parameters:
      - in: path
        name: event_id
        required: true
        type: integer
    responses:
      200:
        description: Participants fetched successfully
      404:
        description: Event not found
    """
    """List participants of an event."""
    event = Event.query.get(event_id)
    if not event:
        return error_response("Event not found", 404)

    participants = [
        {"id": u.id, "username": u.username, "email": u.email}
        for u in event.participants
    ]
    return success_response(participants, "Participants fetched successfully")


# ---------------------------
# RSVP
# ---------------------------
@events_bp.route("/<int:event_id>/rsvp", methods=["POST"])
@token_required
def rsvp_event(current_user, event_id):
    """
    RSVP to an event
    ---
    tags:
      - Events
    parameters:
      - in: path
        name: event_id
        required: true
        type: integer
    responses:
      200:
        description: RSVP successful
      404:
        description: Event not found
      400:
        description: Already RSVPed
    """
    """RSVP to an event."""
    event = Event.query.get(event_id)
    if not event:
        return error_response("Event not found", 404)

    existing = RSVP.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if existing:
        return error_response("Already RSVPed to this event", 400)

    rsvp = RSVP(user_id=current_user.id, event_id=event_id)
    db.session.add(rsvp)
    db.session.commit()
    return success_response(
        {"event_id": event_id, "user_id": current_user.id}, "RSVP successful"
    )


# ---------------------------
# MISSIONS
# ---------------------------
@events_bp.route("/<int:event_id>/missions", methods=["GET"])
def list_missions(event_id):
    """
    List missions for an event
    ---
    tags:
      - Missions
    parameters:
      - in: path
        name: event_id
        required: true
        type: integer
    responses:
      200:
        description: Missions fetched successfully
    """
    """List missions for an event."""
    missions = Mission.query.filter_by(event_id=event_id).all()
    return success_response(
        [mission_to_dict(m) for m in missions], "Missions fetched successfully"
    )


@events_bp.route("/<int:event_id>/missions", methods=["POST"])
@token_required
@roles_required("admin")
def create_mission(current_user, event_id):
    """
    Create a mission for an event (Admin only)
    ---
    tags:
      - Missions
    parameters:
      - in: path
        name: event_id
        required: true
        type: integer
      - in: body
        name: body
        schema:
          type: object
          required: [title, points]
          properties:
            title: {type: string}
            description: {type: string}
            points: {type: integer}
            badge_id: {type: integer}
    responses:
      201:
        description: Mission created successfully
      400:
        description: Invalid input
    """
    """Admin-only: create a mission for an event."""
    data = request.get_json() or {}
    if not data.get("title") or not data.get("points"):
        return error_response("title and points are required", 400)

    mission = Mission(
        title=data["title"],
        description=data.get("description"),
        points=data["points"],
        event_id=event_id,
        badge_id=data.get("badge_id"),
    )
    db.session.add(mission)
    db.session.commit()
    return success_response(
        mission_to_dict(mission), "Mission created successfully", 201
    )

@events_bp.route("/missions/<int:mission_id>/join", methods=["POST"])
@token_required
def join_mission(current_user, mission_id):
    """
    Join a mission
    ---
    tags:
      - Missions
    parameters:
      - in: path
        name: mission_id
        required: true
        type: integer
    responses:
      200:
        description: Mission joined successfully
      404:
        description: Mission not found
      400:
        description: Already joined this mission
    """
    mission = Mission.query.get(mission_id)
    if not mission:
        return error_response("Mission not found", 404)

    existing = MissionParticipant.query.filter_by(user_id=current_user.id, mission_id=mission_id).first()
    if existing:
        return error_response("Already joined this mission", 400)

    participant = MissionParticipant(user_id=current_user.id, mission_id=mission_id, status="joined")
    db.session.add(participant)
    db.session.commit()
    return success_response({"mission_id": mission_id}, "Mission joined successfully")


@events_bp.route("/missions/<int:mission_id>/complete", methods=["POST"])
@token_required
def complete_mission(current_user, mission_id):
    """
    Complete a mission
    ---
    tags:
      - Missions
    parameters:
      - in: path
        name: mission_id
        required: true
        type: integer
    responses:
      200:
        description: Mission completed successfully
      404:
        description: Mission not found
      400:
        description: Already completed or not joined
    """
    mission = Mission.query.get(mission_id)
    if not mission:
        return error_response("Mission not found", 404)

    participant = MissionParticipant.query.filter_by(
        user_id=current_user.id, mission_id=mission_id
    ).first()
    if not participant:
        return error_response("You must join the mission first", 400)
    if participant.status == "completed":
        return error_response("Mission already completed", 400)

    participant.status = "completed"
    participant.completed_at = datetime.utcnow()
    current_user.points += mission.points  # reward points

    db.session.commit()
    return success_response(
        {"mission_id": mission_id, "user_id": current_user.id},
        "Mission completed successfully",
    )


# @events_bp.route("/missions/<int:mission_id>/complete", methods=["POST"])
# @token_required
# def complete_mission(current_user, mission_id):
#     """Mark a mission as completed by the user."""
#     mission = Mission.query.get(mission_id)
#     if not mission:
#         return error_response("Mission not found", 404)

#     existing = MissionProgress.query.filter_by(
#         user_id=current_user.id, mission_id=mission_id
#     ).first()
#     if existing:
#         return error_response("Mission already completed", 400)

#     progress = MissionProgress(user_id=current_user.id, mission_id=mission_id)
#     current_user.points += mission.points  # reward points
#     db.session.add(progress)
#     db.session.commit()
#     return success_response(
#         {"mission_id": mission_id, "user_id": current_user.id},
#         "Mission completed successfully",
#     )
