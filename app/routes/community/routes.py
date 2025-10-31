# app/routes/community/routes.py
from flask import Blueprint, request
from app import db, socketio
from app.models import Zone, Post, Comment, Like, Event, RSVP, User, Era, user_era_membership
from app.utils.decorators import token_required, roles_required
from app.utils.responses import success_response, error_response
from sqlalchemy import func, distinct
from datetime import datetime
from dateutil.relativedelta import relativedelta

community_bp = Blueprint("community", __name__, url_prefix="/community")


# -------------------------------------------------
# ZONES → ERAS (new endpoint name kept for backward compat)
# -------------------------------------------------
@community_bp.route("/zones", methods=["GET"])
@token_required  # works for guests too
def list_zones(current_user=None):
    """
    List all Eras (with member/post counts and joined status)
    ---
    tags:
      - Community
    parameters:
      - name: joined
        in: query
        type: boolean
        description: Filter to eras the current user has joined
    responses:
      200:
        description: List of eras
        schema:
          type: array
          items:
            type: object
            properties:
              id: {type: integer}
              name: {type: string}
              year_range: {type: string}
              description: {type: string}
              image: {type: string}
              member_count: {type: integer}
              post_count: {type: integer}
              joined: {type: boolean}
    """
    joined_only = request.args.get("joined", "").lower() == "true"

    # Base query – always include era + aggregates
    base = (
        db.session.query(
            Era,
            func.count(distinct(Post.id)).label("post_count"),
            func.count(distinct(user_era_membership.c.user_id)).label("member_count"),
        )
        .outerjoin(Zone, Era.id == Zone.era_id)
        .outerjoin(Post, Zone.id == Post.zone_id)
        .outerjoin(user_era_membership, Era.id == user_era_membership.c.era_id)
        .group_by(Era.id)
    )

    # Filter by membership if requested **and** a user is logged in
    if joined_only and current_user:
        base = base.filter(user_era_membership.c.user_id == current_user.id)
    elif joined_only:
        # guest asked for joined → return empty list (no auth)
        return success_response([], "No joined eras for unauthenticated user")

    eras = base.all()

    # Determine joined status per era (O(1) because we already have the join table)
    user_era_ids = {e.id for e in current_user.joined_eras} if current_user else set()

    data = [
        {
            "id": era.id,
            "name": era.name,
            "year_range": era.year_range or "",
            "description": era.description or "",
            "image": era.image or "",
            "member_count": member_count,
            "post_count": post_count,
            "joined": era.id in user_era_ids,
        }
        for era, post_count, member_count in eras
    ]

    return success_response(data, "Eras fetched successfully")


# # ---------------------------
# # ZONES
# # ---------------------------
# @community_bp.route("/zones", methods=["GET"])
# def list_zones():
#     """
#     List all zones
#     ---
#     tags:
#       - Community
#     responses:
#       200:
#         description: Zones fetched successfully
#     """
#     zones = Zone.query.all()
#     data = [{"id": z.id, "name": z.name, "description": z.description} for z in zones]
#     return success_response(data, "Zones fetched successfully")


# @community_bp.route("/zones", methods=["POST"])
# @token_required
# @roles_required("admin")
# def create_zone(current_user):
#     """
#     Create a new zone (Admin only)
#     ---
#     tags:
#       - Community
#     parameters:
#       - in: body
#         name: body
#         schema:
#           type: object
#           required: [name]
#           properties:
#             name: {type: string}
#             description: {type: string}
#     responses:
#       201:
#         description: Zone created successfully
#       400:
#         description: Zone name is required
#       401:
#         description: Unauthorized
#       403:
#         description: Forbidden - Admin role required
#     """
#     data = request.get_json()
#     if not data.get("name"):
#         return error_response("Zone name is required", 400)

#     zone = Zone(name=data["name"], description=data.get("description"))
#     db.session.add(zone)
#     db.session.commit()

#     # 🔴 Emit real-time event
#     socketio.emit(
#         "zone_created",
#         {"id": zone.id, "name": zone.name, "description": zone.description},
#         broadcast=True,
#     )

#     return success_response(message="Zone created successfully", status=201)


@community_bp.route("/zones", methods=["POST"])
@token_required
@roles_required("admin")
def create_zone(current_user):
# def create_zone():
    """
    Create a new **Era** (with optional first Zone)
    ---
    Required: name, year_range
    Optional: description, image, zone_name, zone_description
    """
    data = request.get_json()
    required = ["name", "year_range"]
    if not all(k in data for k in required):
        return error_response("name and year_range are required", 400)

    era = Era(
        name=data["name"],
        year_range=data["year_range"],
        description=data.get("description"),
        image=data.get("image"),
    )
    db.session.add(era)
    db.session.flush()  # get era.id

    # Optional: create first zone
    if data.get("zone_name"):
        zone = Zone(
            name=data["zone_name"],
            description=data.get("zone_description"),
            era_id=era.id,
        )
        db.session.add(zone)

    db.session.commit()

    # Emit era (frontend expects era data)
    socketio.emit(
        "era_created",
        {
            "id": era.id,
            "name": era.name,
            "year_range": era.year_range,
            "description": era.description or "",
            "image": era.image or "",
        },
        # broadcast=True,
    )

    return success_response({"era_id": era.id}, "Era created successfully", status=201)


@community_bp.route("/eras/<int:era_id>/join", methods=["POST"])
@token_required
def join_era(current_user, era_id):
    """
    Join an era
    ---
    tags:
      - Community
    responses:
      200:
        description: Joined successfully
      404:
        description: Era not found
      400:
        description: Already joined
    """
    era = Era.query.get_or_404(era_id)
    if era in current_user.joined_eras:
        return error_response("Already joined", 400)

    current_user.joined_eras.append(era)
    db.session.commit()

    socketio.emit(
        "user_joined_era",
        {
            "user_id": current_user.id,
            "era_id": era.id,
            "username": current_user.username,
        },
        # broadcast=True,
    )

    return success_response(message="Joined era")


# # ---------------------------
# # POSTS
# # ---------------------------
# @community_bp.route("/posts", methods=["POST"])
# @token_required
# def create_post(current_user):
#     """
#     Create a new post
#     ---
#     tags:
#       - Community
#     parameters:
#       - in: body
#         name: body
#         schema:
#           type: object
#           required: [title, content, zone_id]
#           properties:
#             title: {type: string}
#             content: {type: string}
#             zone_id: {type: integer}
#     responses:
#       201:
#         description: Post created successfully
#       400:
#         description: Title, content, and zone_id are required
#       401:
#         description: Unauthorized
#     """
#     data = request.get_json()
#     if not data.get("title") or not data.get("content") or not data.get("zone_id"):
#         return error_response("Title, content, and zone_id are required", 400)

#     post = Post(
#         title=data["title"],
#         content=data["content"],
#         user_id=current_user.id,
#         zone_id=data["zone_id"],
#     )
#     db.session.add(post)
#     db.session.commit()

#     # 🔴 Emit real-time event
#     socketio.emit(
#         "post_created",
#         {
#             "id": post.id,
#             "title": post.title,
#             "content": post.content,
#             "user_id": post.user_id,
#             "zone_id": post.zone_id,
#         },
#         broadcast=True,
#     )

#     return success_response(message="Post created successfully", status=201)


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
        required: true
        schema:
          type: object
          required: [content, era_id]
          properties:
            title:
              type: string
              example: "My first post"
            content:
              type: string
              example: "Check out this retro synth!"
            era_id:
              type: integer
              example: 1
            media:
              type: array
              items:
                type: string
              example: ["data:image/png;base64,iVBORw0KGgo..."]
    responses:
      201:
        description: Post created successfully
        schema:
          type: object
          properties:
            post_id:
              type: integer
              example: 1
      400:
        description: Missing content or era_id
      401:
        description: Unauthorized
      404:
        description: Era not found
    """
    data = request.get_json()
    if not data.get("content") or not data.get("era_id"):
        return error_response("content and era_id are required", 400)

    era = Era.query.get(data["era_id"])
    if not era:
        return error_response("Era not found", 404)

    # Use first zone or create one on-the-fly
    zone = Zone.query.filter_by(era_id=era.id).first()
    if not zone:
        zone = Zone(name=f"{era.name} General", era_id=era.id)
        db.session.add(zone)
        db.session.flush()

    # Store media as |‑separated base64
    media_str = None
    if isinstance(data.get("media"), list):
        media_str = "|".join([m.strip() for m in data["media"] if m.strip()])

    post = Post(
        title=data.get("title", "Untitled"),
        content=data["content"],
        media=media_str,
        user_id=current_user.id,
        zone_id=zone.id,
    )
    db.session.add(post)
    db.session.commit()

    # Emit full post (frontend wants author, time ago, etc.)
    socketio.emit(
        "post_created",
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "media": (post.media.split("|") if post.media else []),
            "created_at": post.created_at.isoformat(),
            "author": {
                "id": current_user.id,
                "username": current_user.username,
                "avatar": current_user.avatar or "",
            },
            "era": {
                "id": era.id,
                "name": era.name,
                "year_range": era.year_range or "",
            },
            "zone": {"id": zone.id, "name": zone.name},
        },
        # broadcast=True,
    )

    return success_response({"post_id": post.id}, "Post created", 201)


def time_ago(dt):
    now = datetime.utcnow()
    diff = relativedelta(now, dt)
    if diff.years > 0:
        return f"{diff.years}y"
    if diff.months > 0:
        return f"{diff.months}mo"
    if diff.days > 0:
        return f"{diff.days}d"
    if diff.hours > 0:
        return f"{diff.hours}h"
    if diff.minutes > 0:
        return f"{diff.minutes}m"
    return "just now"


@community_bp.route("/posts", methods=["GET"])
@token_required
def list_posts(current_user=None):
    """
    List posts with pagination and filters
    ---
    tags:
      - Community
    parameters:
      - name: era_id
        in: query
        type: integer
        example: 1
        description: Filter posts by era
      - name: page
        in: query
        type: integer
        example: 1
        default: 1
      - name: per_page
        in: query
        type: integer
        example: 20
        default: 20
    responses:
      200:
        description: Posts fetched successfully
        schema:
          type: object
          properties:
            posts:
              type: array
              items:
                type: object
                properties:
                  id: {type: integer}
                  title: {type: string}
                  content: {type: string}
                  media:
                    type: array
                    items: {type: string}
                  created_at: {type: string, format: date-time}
                  time_ago: {type: string, example: "2h"}
                  likes_count: {type: integer}
                  comments_count: {type: integer}
                  user_liked: {type: boolean}
                  author:
                    type: object
                    properties:
                      id: {type: integer}
                      username: {type: string}
                      avatar: {type: string}
                  era:
                    type: object
                    properties:
                      id: {type: integer}
                      name: {type: string}
                      year_range: {type: string}
                  zone:
                    type: object
                    properties:
                      id: {type: integer}
                      name: {type: string}
            pagination:
              type: object
              properties:
                page: {type: integer}
                total: {type: integer}
    """
    era_id = request.args.get("era_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = (
        db.session.query(
            Post,
            func.count(distinct(Like.id)).label("likes_count"),
            func.count(distinct(Comment.id)).label("comments_count"),
        )
        .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
        .outerjoin(Comment, Comment.post_id == Post.id)
        .join(Zone, Post.zone_id == Zone.id)
        .join(Era, Zone.era_id == Era.id)
        .group_by(Post.id)
    )
    if era_id:
        query = query.filter(Era.id == era_id)

    paginated = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    user_liked = set()
    if current_user:
        liked = (
            Like.query.filter_by(user_id=current_user.id, type="post")
            .with_entities(Like.post_id)
            .all()
        )
        user_liked = {l[0] for l in liked}

    data = [
        {
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "media": (p.media.split("|") if p.media else []),
            "created_at": p.created_at.isoformat(),
            "time_ago": time_ago(p.created_at),
            "pinned": p.pinned,
            "hot_thread": p.hot_thread,
            "likes_count": likes_count,
            "comments_count": comments_count,
            "user_liked": p.id in user_liked,
            "author": {
                "id": p.user.id,
                "username": p.user.username,
                "avatar": p.user.avatar or "",
            },
            "era": {
                "id": p.zone.era.id,
                "name": p.zone.era.name,
                "year_range": p.zone.era.year_range or "",
            },
            "zone": {"id": p.zone.id, "name": p.zone.name},
        }
        for p, likes_count, comments_count in paginated.items
    ]

    return success_response(
        {"posts": data, "pagination": {"page": page, "total": paginated.total}},
        "Posts fetched",
    )


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
