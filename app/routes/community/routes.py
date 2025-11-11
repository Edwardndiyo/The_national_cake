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


def time_ago(dt):
    """Convert datetime to relative time string"""
    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    elif diff.days > 30:
        return f"{diff.days // 30} months ago"
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return "just now"


@community_bp.route("/zones", methods=["GET"])
@token_required
def list_zones(current_user=None):
    """
    List all Eras (with member/post counts and joined status)
    """

    try:
        print("🔍 DEBUG 1: Starting list_zones endpoint")
        print(f"🔍 DEBUG 2: current_user type: {type(current_user)}")
        print(f"🔍 DEBUG 3: current_user id: {getattr(current_user, 'id', 'NO_ID')}")

        joined_only = request.args.get("joined", "").lower() == "true"
        print(f"🔍 DEBUG 4: joined_only = {joined_only}")

        # Handle joined filter for guest users
        if joined_only and not current_user:
            print("🔍 DEBUG 5: Guest user requested joined eras - returning empty")
            return success_response([], "No joined eras for unauthenticated user")

        # STEP 1: Test basic database connection first
        try:
            print("🔍 DEBUG 6: Testing basic database connection")
            from sqlalchemy import text

            test_result = db.session.execute(text("SELECT 1")).scalar()
            print(f"🔍 DEBUG 7: Database test result: {test_result}")
        except Exception as db_test_error:
            print(f"❌ DEBUG 8: Database connection failed: {db_test_error}")
            return error_response("Database connection failed", 500)

        # STEP 2: Get eras with maximum safety
        eras = []
        try:
            print("🔍 DEBUG 9: Attempting to query eras")
            if joined_only and current_user:
                print(
                    f"🔍 DEBUG 10: Getting joined eras for user_id: {current_user.id}"
                )
                # Use the most basic approach possible
                result = db.session.execute(
                    text(
                        "SELECT era_id FROM user_era_membership WHERE user_id = :user_id"
                    ),
                    {"user_id": current_user.id},
                )
                era_ids = [row[0] for row in result]
                print(f"🔍 DEBUG 11: Found era IDs: {era_ids}")

                if era_ids:
                    # Build query manually to avoid any relationship issues
                    era_id_placeholders = ",".join([str(id) for id in era_ids])
                    era_query = text(
                        f"SELECT * FROM eras WHERE id IN ({era_id_placeholders})"
                    )
                    era_result = db.session.execute(era_query)
                    eras = [dict(row._mapping) for row in era_result]
                    print(f"🔍 DEBUG 12: Found {len(eras)} joined eras as dicts")
                else:
                    eras = []
                    print("🔍 DEBUG 13: No joined eras found")
            else:
                print("🔍 DEBUG 14: Getting all eras")
                # Get all eras as dictionaries to avoid ORM issues
                era_result = db.session.execute(text("SELECT * FROM eras"))
                eras = [dict(row._mapping) for row in era_result]
                print(f"🔍 DEBUG 15: Found {len(eras)} total eras as dicts")

        except Exception as era_error:
            print(f"❌ DEBUG 16: Error in era query: {str(era_error)}")
            import traceback

            print(f"❌ DEBUG 17: Era query traceback:\n{traceback.format_exc()}")
            return error_response(f"Error fetching eras: {str(era_error)}", 500)

        # STEP 3: Get user's joined era IDs
        user_era_ids = set()
        if current_user:
            try:
                print(f"🔍 DEBUG 18: Getting joined era IDs for user {current_user.id}")
                result = db.session.execute(
                    text(
                        "SELECT era_id FROM user_era_membership WHERE user_id = :user_id"
                    ),
                    {"user_id": current_user.id},
                )
                user_era_ids = {row[0] for row in result}
                print(f"🔍 DEBUG 19: User joined era IDs: {user_era_ids}")
            except Exception as user_error:
                print(f"⚠️ DEBUG 20: Error getting user era IDs: {user_error}")
                # Continue without user era IDs

        # STEP 4: Build response data with raw SQL counts
        data = []
        for era_dict in eras:
            try:
                era_id = era_dict["id"]
                print(f"🔍 DEBUG 21: Processing era {era_id}: {era_dict['name']}")

                # Get post count with raw SQL
                try:
                    post_count_result = db.session.execute(
                        text(
                            """
                            SELECT COUNT(*) FROM posts 
                            WHERE zone_id IN (
                                SELECT id FROM zones WHERE era_id = :era_id
                            )
                        """
                        ),
                        {"era_id": era_id},
                    )
                    post_count = post_count_result.scalar() or 0
                    print(f"🔍 DEBUG 22: Era {era_id} post count: {post_count}")
                except Exception as post_error:
                    print(
                        f"⚠️ DEBUG 23: Error getting post count for era {era_id}: {post_error}"
                    )
                    post_count = 0

                # Get member count with raw SQL
                try:
                    member_count_result = db.session.execute(
                        text(
                            "SELECT COUNT(*) FROM user_era_membership WHERE era_id = :era_id"
                        ),
                        {"era_id": era_id},
                    )
                    member_count = member_count_result.scalar() or 0
                    print(f"🔍 DEBUG 24: Era {era_id} member count: {member_count}")
                except Exception as member_error:
                    print(
                        f"⚠️ DEBUG 25: Error getting member count for era {era_id}: {member_error}"
                    )
                    member_count = 0

                era_data = {
                    "id": era_id,
                    "name": era_dict["name"],
                    "year_range": era_dict.get("year_range", ""),
                    "description": era_dict.get("description", ""),
                    "image": era_dict.get("image", ""),
                    "member_count": member_count,
                    "post_count": post_count,
                    "joined": era_id in user_era_ids,
                }
                data.append(era_data)
                print(f"🔍 DEBUG 26: Successfully added era {era_id} to response")

            except Exception as era_process_error:
                print(
                    f"❌ DEBUG 27: Error processing era {era_dict.get('id', 'UNKNOWN')}: {str(era_process_error)}"
                )
                import traceback

                print(f"❌ DEBUG 28: Era process traceback:\n{traceback.format_exc()}")
                continue

        # Build response message
        message = "Eras fetched successfully"
        if joined_only and current_user:
            message = f"Showing {len(data)} joined eras"
        elif not current_user:
            message = "Eras fetched (sign in to join communities)"

        print(f"✅ DEBUG 29: Successfully returning {len(data)} eras")
        return success_response(data, message)

    except Exception as e:
        print(f"❌ CRITICAL DEBUG 30: Top-level error in list_zones: {str(e)}")
        import traceback

        print(f"❌ CRITICAL DEBUG 31: Full traceback:\n{traceback.format_exc()}")
        return error_response(f"Internal server error: {str(e)}", 500)


@community_bp.route("/zones-test", methods=["GET"])
def zones_test():
    """Completely minimal test endpoint"""
    try:
        print("🧪 TEST: Starting zones-test endpoint")
        # Just return a simple response to test if the route works
        test_data = [{"id": 1, "name": "Test Era", "message": "Basic endpoint works"}]
        return success_response(test_data, "Test endpoint working")
    except Exception as e:
        print(f"🧪 TEST ERROR: {e}")
        return error_response(f"Test failed: {str(e)}", 500)


# -------------------------------------------------
# ZONES → ERAS (new endpoint name kept for backward compat)
# -------------------------------------------------
# @community_bp.route("/zones", methods=["GET"])
# @token_required  # works for guests too
# def list_zones(current_user=None):
#     """
#     List all Eras (with member/post counts and joined status)
#     ---
#     tags:
#       - Community
#     parameters:
#       - name: joined
#         in: query
#         type: boolean
#         description: Filter to eras the current user has joined
#     responses:
#       200:
#         description: List of eras
#         schema:
#           type: array
#           items:
#             type: object
#             properties:
#               id: {type: integer}
#               name: {type: string}
#               year_range: {type: string}
#               description: {type: string}
#               image: {type: string}
#               member_count: {type: integer}
#               post_count: {type: integer}
#               joined: {type: boolean}
#     """

#     try:
#         print("🔍 DEBUG: Starting list_zones endpoint")
#         joined_only = request.args.get("joined", "").lower() == "true"
#         print(f"🔍 DEBUG: joined_only = {joined_only}, current_user = {current_user is not None}")

#         # Handle joined filter for guest users
#         if joined_only and not current_user:
#             print("🔍 DEBUG: Guest user requested joined eras - returning empty")
#             return success_response([], "No joined eras for unauthenticated user")

#         # STEP 1: Get eras safely
#         try:
#             if joined_only and current_user:
#                 print("🔍 DEBUG: Getting user's joined eras")
#                 eras = current_user.joined_eras
#                 print(f"🔍 DEBUG: Found {len(eras)} joined eras")
#             else:
#                 print("🔍 DEBUG: Getting all eras")
#                 eras = Era.query.all()
#                 print(f"🔍 DEBUG: Found {len(eras)} total eras")
#         except Exception as era_error:
#             print(f"❌ DEBUG: Error getting eras: {era_error}")
#             return error_response("Error fetching eras", 500)

#         # STEP 2: Get user's joined era IDs safely
#         user_era_ids = set()
#         if current_user:
#             try:
#                 print("🔍 DEBUG: Getting user's joined era IDs")
#                 user_era_ids = {era.id for era in current_user.joined_eras}
#                 print(f"🔍 DEBUG: User has joined {len(user_era_ids)} eras: {user_era_ids}")
#             except Exception as user_error:
#                 print(f"❌ DEBUG: Error getting user eras: {user_error}")
#                 # Continue without user era IDs

#         # STEP 3: Build response data
#         data = []
#         for era in eras:
#             try:
#                 print(f"🔍 DEBUG: Processing era {era.id}: {era.name}")

#                 # Simple counts (skip complex queries for now)
#                 post_count = 0
#                 member_count = 0

#                 # Try to get counts if needed (comment out for now to test)
#                 # post_count = db.session.query(Post).join(Zone).filter(Zone.era_id == era.id).count()
#                 # member_count = db.session.query(user_era_membership).filter(user_era_membership.c.era_id == era.id).count()

#                 era_data = {
#                     "id": era.id,
#                     "name": era.name,
#                     "year_range": era.year_range or "",
#                     "description": era.description or "",
#                     "image": era.image or "",
#                     "member_count": member_count,
#                     "post_count": post_count,
#                     "joined": era.id in user_era_ids,
#                 }
#                 data.append(era_data)
#                 print(f"🔍 DEBUG: Added era {era.id} to response")

#             except Exception as era_process_error:
#                 print(f"❌ DEBUG: Error processing era {era.id}: {era_process_error}")
#                 # Skip this era but continue with others

#         # Build response message
#         message = "Eras fetched successfully"
#         if joined_only and current_user:
#             message = f"Showing {len(data)} joined eras"
#         elif not current_user:
#             message = "Eras fetched (sign in to join communities)"

#         print(f"🔍 DEBUG: Returning {len(data)} eras")
#         return success_response(data, message)

#     except Exception as e:
#         print(f"❌ CRITICAL ERROR in list_zones: {str(e)}")
#         import traceback
#         print(f"❌ FULL TRACEBACK:\n{traceback.format_exc()}")
#         return error_response("Internal server error", 500)

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


@community_bp.route("/posts/my-communities", methods=["GET"])
@token_required
def list_my_community_posts(current_user=None):
    """
    List posts ONLY from eras the current user has joined
    ---
    tags:
      - Community
    parameters:
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
        description: Posts from user's communities fetched successfully
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Get the eras the user has joined
    user_era_ids = [era.id for era in current_user.joined_eras]

    if not user_era_ids:
        return success_response(
            {"posts": [], "pagination": {"page": page, "total": 0}},
            "No posts found - user hasn't joined any communities"
        )

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
        .filter(Era.id.in_(user_era_ids))  # ✅ Only user's joined eras
        .group_by(Post.id)
    )

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
        "Posts from your communities fetched",
    )


@community_bp.route("/posts/all", methods=["GET"])
@token_required
def list_all_posts(current_user=None):
    """
    List ALL posts from ALL eras (discover/explore feed)
    ---
    tags:
      - Community
    parameters:
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
        description: All posts fetched successfully
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # FIX: Add explicit joins for User and Era
    query = (
        db.session.query(
            Post,
            User,  # Add User to the query
            Zone,
            Era,  # Add Era to the query
            func.count(distinct(Like.id)).label("likes_count"),
            func.count(distinct(Comment.id)).label("comments_count"),
        )
        .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
        .outerjoin(Comment, Comment.post_id == Post.id)
        .join(User, Post.user_id == User.id)  # Explicit join for User
        .join(Zone, Post.zone_id == Zone.id)
        .join(Era, Zone.era_id == Era.id)  # Explicit join for Era
        .group_by(Post.id, User.id, Zone.id, Era.id)  # Group by all selected tables
    )

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

    # FIX: Now we have post, user, zone, and era objects from the query
    data = [
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "media": (post.media.split("|") if post.media else []),
            "created_at": post.created_at.isoformat(),
            "time_ago": time_ago(post.created_at),
            "pinned": post.pinned,
            "hot_thread": post.hot_thread,
            "likes_count": likes_count,
            "comments_count": comments_count,
            "user_liked": post.id in user_liked,
            "author": {
                "id": user.id,  # Use user from query
                "username": user.username,  # Use user from query
                "avatar": user.avatar or "",
            },
            "era": {
                "id": era.id,  # Use era from query
                "name": era.name,  # Use era from query
                "year_range": era.year_range or "",  # Use era from query
            },
            "zone": {"id": zone.id, "name": zone.name},  # Use zone from query
        }
        for post, user, zone, era, likes_count, comments_count in paginated.items
    ]

    return success_response(
        {"posts": data, "pagination": {"page": page, "total": paginated.total}},
        "All posts fetched",
    )
    # page = request.args.get("page", 1, type=int)
    # per_page = request.args.get("per_page", 20, type=int)

    # query = (
    #     db.session.query(
    #         Post,
    #         func.count(distinct(Like.id)).label("likes_count"),
    #         func.count(distinct(Comment.id)).label("comments_count"),
    #     )
    #     .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
    #     .outerjoin(Comment, Comment.post_id == Post.id)
    #     .join(Zone, Post.zone_id == Zone.id)
    #     .join(Era, Zone.era_id == Era.id)
    #     .group_by(Post.id)
    # )

    # paginated = query.order_by(Post.created_at.desc()).paginate(
    #     page=page, per_page=per_page, error_out=False
    # )

    # user_liked = set()
    # if current_user:
    #     liked = (
    #         Like.query.filter_by(user_id=current_user.id, type="post")
    #         .with_entities(Like.post_id)
    #         .all()
    #     )
    #     user_liked = {l[0] for l in liked}

    # data = [
    #     {
    #         "id": p.id,
    #         "title": p.title,
    #         "content": p.content,
    #         "media": (p.media.split("|") if p.media else []),
    #         "created_at": p.created_at.isoformat(),
    #         "time_ago": time_ago(p.created_at),
    #         "pinned": p.pinned,
    #         "hot_thread": p.hot_thread,
    #         "likes_count": likes_count,
    #         "comments_count": comments_count,
    #         "user_liked": p.id in user_liked,
    #         "author": {
    #             "id": p.user.id,
    #             "username": p.user.username,
    #             "avatar": p.user.avatar or "",
    #         },
    #         "era": {
    #             "id": p.zone.era.id,
    #             "name": p.zone.era.name,
    #             "year_range": p.zone.era.year_range or "",
    #         },
    #         "zone": {"id": p.zone.id, "name": p.zone.name},
    #     }
    #     for p, likes_count, comments_count in paginated.items
    # ]

    # return success_response(
    #     {"posts": data, "pagination": {"page": page, "total": paginated.total}},
    #     "All posts fetched",
    # )


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
    
    # If no era_id specified, default to user's communities
    if not era_id and current_user:
        user_era_ids = [era.id for era in current_user.joined_eras]
        if user_era_ids:
            query = query.filter(Era.id.in_(user_era_ids))
            
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
