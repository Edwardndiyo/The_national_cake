# app/routes/community/routes.py
from flask import Blueprint, request
from app import db, socketio
from app.models import Zone, Post, Comment, Like, Event, RSVP, User
from app.utils.decorators import token_required, roles_required
from app.utils.responses import success_response, error_response
from sqlalchemy import func

community_bp = Blueprint("community", __name__, url_prefix="/community")


# ---------------------------
# ZONES
# ---------------------------
@community_bp.route("/zones", methods=["GET"])
def list_zones():
    """
    List all zones
    ---
    tags:
      - Community
    responses:
      200:
        description: Zones fetched successfully
    """
    zones = Zone.query.all()
    data = [{"id": z.id, "name": z.name, "description": z.description} for z in zones]
    return success_response(data, "Zones fetched successfully")


@community_bp.route("/zones", methods=["POST"])
@token_required
@roles_required("admin")
def create_zone(current_user):
    """
    Create a new zone (Admin only)
    ---
    tags:
      - Community
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [name]
          properties:
            name: {type: string}
            description: {type: string}
    responses:
      201:
        description: Zone created successfully
      400:
        description: Zone name is required
      401:
        description: Unauthorized
      403:
        description: Forbidden - Admin role required
    """
    data = request.get_json()
    if not data.get("name"):
        return error_response("Zone name is required", 400)

    zone = Zone(name=data["name"], description=data.get("description"))
    db.session.add(zone)
    db.session.commit()

    # 🔴 Emit real-time event
    socketio.emit(
        "zone_created",
        {"id": zone.id, "name": zone.name, "description": zone.description},
        broadcast=True,
    )

    return success_response(message="Zone created successfully", status=201)


# ---------------------------
# POSTS
# ---------------------------
@community_bp.route("/posts", methods=["POST"])
@token_required
def create_post(current_user):
    """
    Create a new post
    ---
    tags:
      - Community
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [title, content, zone_id]
          properties:
            title: {type: string}
            content: {type: string}
            zone_id: {type: integer}
    responses:
      201:
        description: Post created successfully
      400:
        description: Title, content, and zone_id are required
      401:
        description: Unauthorized
    """
    data = request.get_json()
    if not data.get("title") or not data.get("content") or not data.get("zone_id"):
        return error_response("Title, content, and zone_id are required", 400)

    post = Post(
        title=data["title"],
        content=data["content"],
        user_id=current_user.id,
        zone_id=data["zone_id"],
    )
    db.session.add(post)
    db.session.commit()

    # 🔴 Emit real-time event
    socketio.emit(
        "post_created",
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "user_id": post.user_id,
            "zone_id": post.zone_id,
        },
        broadcast=True,
    )

    return success_response(message="Post created successfully", status=201)


@community_bp.route("/posts/<int:post_id>", methods=["DELETE"])
@token_required
@roles_required("admin")
def delete_post(current_user, post_id):
    """
    Delete a post (Admin only)
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Post deleted successfully
      401:
        description: Unauthorized
      403:
        description: Forbidden - Admin role required
      404:
        description: Post not found
    """
    post = Post.query.get(post_id)
    if not post:
        return error_response("Post not found", 404)

    db.session.delete(post)
    db.session.commit()

    # 🔴 Emit real-time event
    socketio.emit("post_deleted", {"id": post_id}, broadcast=True)

    return success_response(message="Post deleted successfully")


# ---------------------------
# COMMENTS
# ---------------------------
@community_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
@token_required
def add_comment(current_user, post_id):
    """
    Add a comment to a post
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
      - in: body
        name: body
        schema:
          type: object
          required: [content]
          properties:
            content: {type: string}
    responses:
      201:
        description: Comment added successfully
      400:
        description: Content is required
      401:
        description: Unauthorized
      404:
        description: Post not found
    """
    data = request.get_json()
    if not data.get("content"):
        return error_response("Content is required", 400)

    comment = Comment(content=data["content"], user_id=current_user.id, post_id=post_id)
    db.session.add(comment)
    db.session.commit()

    # 🔴 Emit real-time event
    socketio.emit(
        "comment_added",
        {
            "id": comment.id,
            "content": comment.content,
            "user_id": comment.user_id,
            "post_id": comment.post_id,
        },
        broadcast=True,
    )

    return success_response(message="Comment added successfully", status=201)


# ---------------------------
# LIKES
# ---------------------------
@community_bp.route("/posts/<int:post_id>/like", methods=["POST"])
@token_required
def toggle_like(current_user, post_id):
    """
    Like or unlike a post
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
    responses:
      201:
        description: Post liked
      200:
        description: Post unliked
      401:
        description: Unauthorized
      404:
        description: Post not found
    """
    existing_like = Like.query.filter_by(
        user_id=current_user.id, post_id=post_id
    ).first()

    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()

        # 🔴 Emit unlike event
        socketio.emit(
            "post_unliked",
            {"post_id": post_id, "user_id": current_user.id},
            broadcast=True,
        )

        return success_response(message="Unliked")
    else:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()

        # 🔴 Emit like event
        socketio.emit(
            "post_liked",
            {"post_id": post_id, "user_id": current_user.id},
            broadcast=True,
        )

        return success_response(message="Liked", status=201)


# ---------------------------
# EVENTS
# ---------------------------
@community_bp.route("/events", methods=["POST"])
@token_required
@roles_required("admin")
def create_event(current_user):
    """
    Create a new event (Admin only)
    ---
    tags:
      - Community
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [title, event_date]
          properties:
            title: {type: string}
            description: {type: string}
            event_date: {type: string, format: date-time}
    responses:
      201:
        description: Event created successfully
      400:
        description: Title and event_date are required
      401:
        description: Unauthorized
      403:
        description: Forbidden - Admin role required
    """
    data = request.get_json()
    if not data.get("title") or not data.get("event_date"):
        return error_response("Title and event_date are required", 400)

    event = Event(
        title=data["title"],
        description=data.get("description"),
        event_date=data["event_date"],
    )
    db.session.add(event)
    db.session.commit()

    # 🔴 Emit real-time event
    socketio.emit(
        "event_created",
        {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "event_date": str(event.event_date),
        },
        broadcast=True,
    )

    return success_response(message="Event created successfully", status=201)


@community_bp.route("/events/<int:event_id>/rsvp", methods=["POST"])
@token_required
def rsvp_event(current_user, event_id):
    """
    RSVP to an event
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: event_id
        required: true
        schema:
          type: integer
      - in: body
        name: body
        schema:
          type: object
          required: [status]
          properties:
            status: {type: string, enum: [going, interested, not_going]}
    responses:
      200:
        description: RSVP updated successfully
      400:
        description: Status is required
      401:
        description: Unauthorized
      404:
        description: Event not found
    """
    data = request.get_json()
    if not data.get("status"):
        return error_response("Status is required (going, interested, not_going)", 400)

    rsvp = RSVP.query.filter_by(user_id=current_user.id, event_id=event_id).first()
    if rsvp:
        rsvp.status = data["status"]
    else:
        rsvp = RSVP(status=data["status"], user_id=current_user.id, event_id=event_id)
        db.session.add(rsvp)

    db.session.commit()

    # 🔴 Emit real-time event
    socketio.emit(
        "event_rsvp",
        {"event_id": event_id, "user_id": current_user.id, "status": data["status"]},
        broadcast=True,
    )

    return success_response(message="RSVP updated successfully")


# ---------------------------
# COMMUNITY EXTRA ENDPOINTS
# ---------------------------
@community_bp.route("/<int:zone_id>/members", methods=["GET"])
@token_required
def get_community_members(current_user, zone_id):
    """
    Get members of a community zone
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: zone_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Community members fetched successfully
      401:
        description: Unauthorized
      404:
        description: Community not found
    """
    zone = Zone.query.get(zone_id)
    if not zone:
        return error_response("Community not found", 404)

    members = (
        db.session.query(
            User.id,
            User.username,
            User.fullname,
            User.role,
            func.min(Post.created_at).label("joined_at"),
        )
        .join(Post, Post.user_id == User.id)
        .filter(Post.zone_id == zone_id)
        .group_by(User.id, User.username, User.fullname, User.role)
        .all()
    )

    data = [
        {
            "id": m.id,
            "username": m.username,
            "fullname": m.fullname,
            "role": m.role,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m in members
    ]
    return success_response(data, "Community members fetched successfully")


@community_bp.route("/<int:zone_id>/posts", methods=["GET"])
@token_required
def get_community_posts(current_user, zone_id):
    """
    Get posts in a community zone
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: zone_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Community posts fetched successfully
      401:
        description: Unauthorized
      404:
        description: Community not found
    """
    zone = Zone.query.get(zone_id)
    if not zone:
        return error_response("Community not found", 404)

    posts = Post.query.filter_by(zone_id=zone.id).all()
    data = [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "pinned": p.pinned,
            "hot_thread": p.hot_thread,
            "created_at": p.created_at.isoformat(),
            "user_id": p.user_id,
        }
        for p in posts
    ]
    return success_response(data, "Community posts fetched successfully")


@community_bp.route("/<int:zone_id>/comments", methods=["GET"])
@token_required
def get_community_comments(current_user, zone_id):
    """
    Get comments in a community zone
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: zone_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Community comments fetched successfully
      401:
        description: Unauthorized
      404:
        description: Community not found
    """
    zone = Zone.query.get(zone_id)
    if not zone:
        return error_response("Community not found", 404)

    comments = (
        db.session.query(Comment)
        .join(Post, Post.id == Comment.post_id)
        .filter(Post.zone_id == zone.id)
        .all()
    )

    data = [
        {
            "id": c.id,
            "content": c.content,
            "created_at": c.created_at.isoformat(),
            "user_id": c.user_id,
            "post_id": c.post_id,
        }
        for c in comments
    ]
    return success_response(data, "Community comments fetched successfully")


@community_bp.route("/<int:zone_id>/stats", methods=["GET"])
@token_required
def get_community_stats(current_user, zone_id):
    """
    Get statistics for a community zone
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: zone_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Community stats fetched successfully
      401:
        description: Unauthorized
      404:
        description: Community not found
    """
    zone = Zone.query.get(zone_id)
    if not zone:
        return error_response("Community not found", 404)

    total_posts = Post.query.filter_by(zone_id=zone.id).count()
    total_comments = (
        db.session.query(Comment)
        .join(Post, Post.id == Comment.post_id)
        .filter(Post.zone_id == zone.id)
        .count()
    )
    total_members = (
        db.session.query(User.id)
        .join(Post, Post.user_id == User.id)
        .filter(Post.zone_id == zone.id)
        .distinct()
        .count()
    )

    stats = {
        "community_id": zone.id,
        "name": zone.name,
        "total_posts": total_posts,
        "total_comments": total_comments,
        "total_members": total_members,
    }
    return success_response(stats, "Community stats fetched successfully")
