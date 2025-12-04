# app/routes/community/routes.py
from flask import Blueprint, request
from flask_jwt_extended import current_user
from app import db, socketio
from app.models import Reshare, Zone, Post, Comment, Like, Event, RSVP, User, Era, user_era_membership, Badge,Bookmark
from app.utils.decorators import token_required, roles_required
from app.utils.responses import success_response, error_response
from sqlalchemy import case, func, distinct, text
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sqlalchemy as sa
from sqlalchemy import func, distinct
from sqlalchemy.orm import joinedload


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


# @community_bp.route("/zones", methods=["GET"])
# @token_required
# def list_zones(current_user=None):
#     """
#     List all Eras (with member/post counts and joined status)
#     """

#     try:
#         print("🔍 DEBUG 1: Starting list_zones endpoint")
#         print(f"🔍 DEBUG 2: current_user type: {type(current_user)}")
#         print(f"🔍 DEBUG 3: current_user id: {getattr(current_user, 'id', 'NO_ID')}")

#         joined_only = request.args.get("joined", "").lower() == "true"
#         print(f"🔍 DEBUG 4: joined_only = {joined_only}")

#         # Handle joined filter for guest users
#         if joined_only and not current_user:
#             print("🔍 DEBUG 5: Guest user requested joined eras - returning empty")
#             return success_response([], "No joined eras for unauthenticated user")

#         # STEP 1: Test basic database connection first
#         try:
#             print("🔍 DEBUG 6: Testing basic database connection")
#             from sqlalchemy import text

#             test_result = db.session.execute(text("SELECT 1")).scalar()
#             print(f"🔍 DEBUG 7: Database test result: {test_result}")
#         except Exception as db_test_error:
#             print(f"❌ DEBUG 8: Database connection failed: {db_test_error}")
#             return error_response("Database connection failed", 500)

#         # STEP 2: Get eras with maximum safety
#         eras = []
#         try:
#             print("🔍 DEBUG 9: Attempting to query eras")
#             if joined_only and current_user:
#                 print(
#                     f"🔍 DEBUG 10: Getting joined eras for user_id: {current_user.id}"
#                 )
#                 # Use the most basic approach possible
#                 result = db.session.execute(
#                     text(
#                         "SELECT era_id FROM user_era_membership WHERE user_id = :user_id"
#                     ),
#                     {"user_id": current_user.id},
#                 )
#                 era_ids = [row[0] for row in result]
#                 print(f"🔍 DEBUG 11: Found era IDs: {era_ids}")

#                 if era_ids:
#                     # Build query manually to avoid any relationship issues
#                     era_id_placeholders = ",".join([str(id) for id in era_ids])
#                     era_query = text(
#                         f"SELECT * FROM eras WHERE id IN ({era_id_placeholders})"
#                     )
#                     era_result = db.session.execute(era_query)
#                     eras = [dict(row._mapping) for row in era_result]
#                     print(f"🔍 DEBUG 12: Found {len(eras)} joined eras as dicts")
#                 else:
#                     eras = []
#                     print("🔍 DEBUG 13: No joined eras found")
#             else:
#                 print("🔍 DEBUG 14: Getting all eras")
#                 # Get all eras as dictionaries to avoid ORM issues
#                 era_result = db.session.execute(text("SELECT * FROM eras"))
#                 eras = [dict(row._mapping) for row in era_result]
#                 print(f"🔍 DEBUG 15: Found {len(eras)} total eras as dicts")

#         except Exception as era_error:
#             print(f"❌ DEBUG 16: Error in era query: {str(era_error)}")
#             import traceback

#             print(f"❌ DEBUG 17: Era query traceback:\n{traceback.format_exc()}")
#             return error_response(f"Error fetching eras: {str(era_error)}", 500)

#         # STEP 3: Get user's joined era IDs
#         user_era_ids = set()
#         if current_user:
#             try:
#                 print(f"🔍 DEBUG 18: Getting joined era IDs for user {current_user.id}")
#                 result = db.session.execute(
#                     text(
#                         "SELECT era_id FROM user_era_membership WHERE user_id = :user_id"
#                     ),
#                     {"user_id": current_user.id},
#                 )
#                 user_era_ids = {row[0] for row in result}
#                 print(f"🔍 DEBUG 19: User joined era IDs: {user_era_ids}")
#             except Exception as user_error:
#                 print(f"⚠️ DEBUG 20: Error getting user era IDs: {user_error}")
#                 # Continue without user era IDs

#         # STEP 4: Build response data with raw SQL counts
#         data = []
#         for era_dict in eras:
#             try:
#                 era_id = era_dict["id"]
#                 print(f"🔍 DEBUG 21: Processing era {era_id}: {era_dict['name']}")

#                 # Get post count with raw SQL
#                 try:
#                     post_count_result = db.session.execute(
#                         text(
#                             """
#                             SELECT COUNT(*) FROM posts
#                             WHERE zone_id IN (
#                                 SELECT id FROM zones WHERE era_id = :era_id
#                             )
#                         """
#                         ),
#                         {"era_id": era_id},
#                     )
#                     post_count = post_count_result.scalar() or 0
#                     print(f"🔍 DEBUG 22: Era {era_id} post count: {post_count}")
#                 except Exception as post_error:
#                     print(
#                         f"⚠️ DEBUG 23: Error getting post count for era {era_id}: {post_error}"
#                     )
#                     post_count = 0

#                 # Get member count with raw SQL
#                 try:
#                     member_count_result = db.session.execute(
#                         text(
#                             "SELECT COUNT(*) FROM user_era_membership WHERE era_id = :era_id"
#                         ),
#                         {"era_id": era_id},
#                     )
#                     member_count = member_count_result.scalar() or 0
#                     print(f"🔍 DEBUG 24: Era {era_id} member count: {member_count}")
#                 except Exception as member_error:
#                     print(
#                         f"⚠️ DEBUG 25: Error getting member count for era {era_id}: {member_error}"
#                     )
#                     member_count = 0

#                 era_data = {
#                     "id": era_id,
#                     "name": era_dict["name"],
#                     "year_range": era_dict.get("year_range", ""),
#                     "description": era_dict.get("description", ""),
#                     "image": era_dict.get("image", ""),
#                     "member_count": member_count,
#                     "post_count": post_count,
#                     "joined": era_id in user_era_ids,
#                 }
#                 data.append(era_data)
#                 print(f"🔍 DEBUG 26: Successfully added era {era_id} to response")

#             except Exception as era_process_error:
#                 print(
#                     f"❌ DEBUG 27: Error processing era {era_dict.get('id', 'UNKNOWN')}: {str(era_process_error)}"
#                 )
#                 import traceback

#                 print(f"❌ DEBUG 28: Era process traceback:\n{traceback.format_exc()}")
#                 continue

#         # Build response message
#         message = "Eras fetched successfully"
#         if joined_only and current_user:
#             message = f"Showing {len(data)} joined eras"
#         elif not current_user:
#             message = "Eras fetched (sign in to join communities)"

#         print(f"✅ DEBUG 29: Successfully returning {len(data)} eras")
#         return success_response(data, message)

#     except Exception as e:
#         print(f"❌ CRITICAL DEBUG 30: Top-level error in list_zones: {str(e)}")
#         import traceback

#         print(f"❌ CRITICAL DEBUG 31: Full traceback:\n{traceback.format_exc()}")
#         return error_response(f"Internal server error: {str(e)}", 500)

@community_bp.route("/zones", methods=["GET"])
@token_required
def list_zones(current_user=None):
    joined_only = request.args.get("joined", "").lower() == "true"

    if joined_only and not current_user:
        return success_response([], "No joined eras")

    query = Era.query.options(
        joinedload(Era.members),
        joinedload(Era.zones).joinedload(Zone.posts)
    )

    if joined_only and current_user:
        query = query.filter(Era.members.any(User.id == current_user.id))

    eras = query.all()

    # Get joined era IDs directly from association table (most reliable)
    user_era_ids = set()
    if current_user:
        result = db.session.execute(
            text("SELECT era_id FROM user_era_membership WHERE user_id = :uid"),
            {"uid": current_user.id}
        )
        user_era_ids = {row[0] for row in result}

    data = [
        {
            "id": era.id,
            "name": era.name,
            "year_range": era.year_range or "",
            "description": era.description or "",
            "image": era.image or "",
            "member_count": len(era.members),
            "post_count": sum(len(zone.posts) for zone in era.zones),
            "joined": era.id in user_era_ids,
        }
        for era in eras
    ]

    return success_response(data, "Eras fetched successfully")
  
  
# @community_bp.route("/zones", methods=["GET"])
# @token_required
# def list_zones(current_user=None):
#     """
#     List all Eras with proper joined status using real relationships
#     """
#     joined_only = request.args.get("joined", "").lower() == "true"

#     # For guests + joined_only → return empty
#     if joined_only and not current_user:
#         return success_response([], "No joined eras for unauthenticated user")

#     # 1. Get base query
#     query = Era.query

#     # 2. If joined_only → filter to user's joined eras
#     if joined_only and current_user:
#         query = query.filter(Era.members.any(User.id == current_user.id))
#     #    ^^^ This uses the actual many-to-many relationship correctly ^^^

#     eras = query.all()

#     # 3. Get user's joined era IDs once (efficiently)
#     user_era_ids = set()
#     if current_user:
#         user_era_ids = {era.id for era in current_user.joined_eras}
#         # This loads the relationship properly — no raw SQL needed

#     # 4. Build response with real counts using proper joins
#     data = []
#     for era in eras:
#         data.append(
#             {
#                 "id": era.id,
#                 "name": era.name,
#                 "year_range": era.year_range or "",
#                 "description": era.description or "",
#                 "image": era.image or "",
#                 "member_count": len(era.members),  # Real count
#                 "post_count": sum(len(zone.posts) for zone in era.zones),  # Real count
#                 "joined": era.id in user_era_ids,  # Correct!
#             }
#         )

#     message = "Eras fetched successfully"
#     if joined_only:
#         message = f"Showing {len(data)} joined eras"
#     elif not current_user:
#         message = "Eras fetched (sign in to join communities)"

#     return success_response(data, message)


@community_bp.route("/eras/<int:era_id>", methods=["GET"])
@token_required
def get_single_era(current_user, era_id):
    """
    Get a single era by ID with member and post counts
    ---
    tags:
      - Community
    parameters:
      - name: era_id
        in: path
        type: integer
        required: true
        description: ID of the era to retrieve
    responses:
      200:
        description: Era fetched successfully
      404:
        description: Era not found
    """
    # Get the era
    era = Era.query.get(era_id)
    if not era:
        return error_response("Era not found", 404)

    # Get post count
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

    # Get member count
    member_count_result = db.session.execute(
        text("SELECT COUNT(*) FROM user_era_membership WHERE era_id = :era_id"),
        {"era_id": era_id},
    )
    member_count = member_count_result.scalar() or 0

    # Check if current user has joined this era
    joined = False
    if current_user:
        membership_result = db.session.execute(
            text(
                "SELECT 1 FROM user_era_membership WHERE user_id = :user_id AND era_id = :era_id"
            ),
            {"user_id": current_user.id, "era_id": era_id},
        )
        joined = membership_result.first() is not None

    # Get zones for this era
    zones = Zone.query.filter_by(era_id=era_id).all()
    zones_data = [
        {
            "id": zone.id,
            "name": zone.name,
            "description": zone.description or "",
        }
        for zone in zones
    ]

    era_data = {
        "id": era.id,
        "name": era.name,
        "year_range": era.year_range or "",
        "description": era.description or "",
        "image": era.image or "",
        "member_count": member_count,
        "post_count": post_count,
        "joined": joined,
        "zones": zones_data,
    }

    return success_response(era_data, "Era fetched successfully")

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


# @community_bp.route("/eras/<int:era_id>/join", methods=["POST"])
# @token_required
# def join_era(current_user, era_id):
#     """
#     Join an era
#     ---
#     tags:
#       - Community
#     responses:
#       200:
#         description: Joined successfully
#       404:
#         description: Era not found
#       400:
#         description: Already joined
#     """
#     era = Era.query.get_or_404(era_id)
#     if era in current_user.joined_eras:
#         return error_response("Already joined", 400)

#     current_user.joined_eras.append(era)
#     db.session.commit()

#     socketio.emit(
#         "user_joined_era",
#         {
#             "user_id": current_user.id,
#             "era_id": era.id,
#             "username": current_user.username,
#         },
#         # broadcast=True,
#     )

#     return success_response(message="Joined era")

@community_bp.route("/eras/<int:era_id>/join", methods=["POST"])
@token_required
def join_era(current_user: User, era_id: int):
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
      401:
        description: Authentication required
    """
    era = Era.query.get_or_404(era_id)

    # NEVER trust current_user.joined_eras in production
    # Instead query the association table directly (one fast query)
    already_joined = db.session.execute(
        text("SELECT 1 FROM user_era_membership WHERE user_id = :uid AND era_id = :eid"),
        {"uid": current_user.id, "eid": era.id}
    ).scalar() is not None

    if already_joined:
        return error_response("You have already joined this era", 400)

    # Insert the membership row explicitly (guaranteed to work)
    db.session.execute(
        text("INSERT INTO user_era_membership (user_id, era_id) VALUES (:uid, :eid)"),
        {"uid": current_user.id, "eid": era.id}
    )
    db.session.commit()

    # Now emit the event
    socketio.emit(
        "user_joined_era",
        {
            "user_id": current_user.id,
            "username": current_user.username,
            "era_id": era.id,
            "message": f"{current_user.username} joined the era!"
        },
        to=f"era_{era.id}"
    )

    return success_response(message="Successfully joined the era!")
  


    # era = Era.query.get_or_404(era_id)

    # if era in current_user.joined_eras:
    #     return error_response("You have already joined this era", 400)

    # current_user.joined_eras.append(era)
    # db.session.commit()

    # # Emit to everyone in the era (or use rooms for scalability)
    # socketio.emit(
    #     "user_joined_era",
    #     {
    #         "user_id": current_user.id,
    #         "username": current_user.username,
    #         "era_id": era.id,
    #         "message": f"{current_user.username} joined the era!"
    #     },
    #     to=f"era_{era.id}"  # Recommended: use SocketIO rooms
    # )

    # return success_response(message="Successfully joined the era!")
  

@community_bp.route("/eras/<int:era_id>/leave", methods=["POST"])
@token_required
def leave_era(current_user: User, era_id: int):
    """
    Leave an era
    ---
    tags:
      - Community
    responses:
      200:
        description: Left successfully
      404:
        description: Era not found
      400:
        description: Not a member
      401:
        description: Authentication required
    """
    era = Era.query.get_or_404(era_id)

    result = db.session.execute(
        text("DELETE FROM user_era_membership WHERE user_id = :uid AND era_id = :eid"),
        {"uid": current_user.id, "eid": era.id}
    )
    db.session.commit()

    if result.rowcount == 0:
        return error_response("You are not a member of this era", 400)

    socketio.emit("user_left_era", {
        "user_id": current_user.id,
        "username": current_user.username,
        "era_id": era.id
    }, to=f"era_{era.id}")

    return success_response(message="Left the era successfully")
  
  
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
            "time_ago": time_ago(post.created_at),
        "pinned": post.pinned,
        "hot_thread": post.hot_thread,
        "likes_count": 0,  # New posts start with 0
        "agree_count": 0,  # New posts start with 0
        "disagree_count": 0,  # New posts start with 0
        "comments_count": 0,  # New posts start with 0
        "user_agreed": False,
        "user_disagreed": False,
        
            "author": {
                "id": current_user.id,
                # "fullname": current_user.fullname,
                "firstname": current_user.firstname,
                "lastname": current_user.lastname,
                
                
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


# ---------------------------
# GET COMMENTS FOR POST
# ---------------------------
@community_bp.route("/posts/<int:post_id>/comments", methods=["GET"])
@token_required
def get_post_comments(current_user, post_id):
    """
    Get all comments for a specific post with nested replies
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
        description: Comments fetched successfully
      404:
        description: Post not found
    """
    post = Post.query.get(post_id)
    if not post:
        return error_response("Post not found", 404)

    # Get top-level comments (comments without parents)
    top_level_comments = (
        Comment.query.filter_by(post_id=post_id, parent_comment_id=None)
        .order_by(Comment.created_at.asc())
        .all()
    )

    def build_comment_tree(comment):
        """Recursively build comment tree with replies"""
        user = User.query.get(comment.user_id)
        comment_data = {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "time_ago": time_ago(comment.created_at),
            "author": {
                "id": user.id,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "username": user.username,
                "avatar": user.avatar or "",
            },
            "replies": []
        }
        
        # Get replies for this comment
        replies = Comment.query.filter_by(parent_comment_id=comment.id)\
                              .order_by(Comment.created_at.asc())\
                              .all()
        
        for reply in replies:
            comment_data["replies"].append(build_comment_tree(reply))
            
        return comment_data

    # Build the comment tree
    data = []
    for comment in top_level_comments:
        data.append(build_comment_tree(comment))

    return success_response(data, "Comments fetched successfully")


# @community_bp.route("/posts/<int:post_id>/comments", methods=["GET"])
# @token_required
# def get_post_comments(current_user, post_id):
#     """
#     Get all comments for a specific post
#     ---
#     tags:
#       - Community
#     parameters:
#       - in: path
#         name: post_id
#         required: true
#         schema:
#           type: integer
#     responses:
#       200:
#         description: Comments fetched successfully
#       404:
#         description: Post not found
#     """
#     post = Post.query.get(post_id)
#     if not post:
#         return error_response("Post not found", 404)

#     comments = (
#         Comment.query.filter_by(post_id=post_id)
#         .order_by(Comment.created_at.asc())
#         .all()
#     )

#     data = []
#     for comment in comments:
#         user = User.query.get(comment.user_id)
#         data.append(
#             {
#                 "id": comment.id,
#                 "content": comment.content,
#                 "created_at": comment.created_at.isoformat(),
#                 "time_ago": time_ago(comment.created_at),
#                 "author": {
#                     "id": user.id,
#                     "firstname": user.firstname,
#                     "lastname": user.lastname,
#                     "username": user.username,
#                     "avatar": user.avatar or "",
#                 },
#             }
#         )

#     return success_response(data, "Comments fetched successfully")


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
            "No posts found - user hasn't joined any communities",
        )

    query = (
        db.session.query(
            Post,
            User,  # Post author
            Zone,
            Era,
            func.count(distinct(Like.id)).label("likes_count"),
            func.count(
                distinct(case((Like.reaction_type == "agree", Like.id), else_=None))
            ).label("agree_count"),
            func.count(
                distinct(case((Like.reaction_type == "disagree", Like.id), else_=None))
            ).label("disagree_count"),
            func.count(distinct(Comment.id)).label("comments_count"),
        )
        .join(User, Post.user_id == User.id)  # Join with User to get author
        .join(Zone, Post.zone_id == Zone.id)
        .join(Era, Zone.era_id == Era.id)
        .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
        .outerjoin(Comment, Comment.post_id == Post.id)
        .filter(Era.id.in_(user_era_ids))
        .group_by(Post.id, User.id, Zone.id, Era.id)
    )

    paginated = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    user_reactions = {}
    bookmarked_posts = set()

    post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
    if post_ids:
        # Get user reactions
        reactions = Like.query.filter(
            Like.user_id == current_user.id,
            Like.post_id.in_(post_ids),
            Like.type == "post",
        ).all()
        user_reactions = {r.post_id: r.reaction_type for r in reactions}

        # Get bookmarked posts
        bookmarks = Bookmark.query.filter(
            Bookmark.user_id == current_user.id, Bookmark.post_id.in_(post_ids)
        ).all()
        bookmarked_posts = {bm.post_id for bm in bookmarks}

    data = []
    if current_user:
            post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
            if post_ids:
                reshares = Reshare.query.filter(
                    Reshare.user_id == current_user.id,
                    Reshare.post_id.in_(post_ids)
                ).all()
                user_reshared_posts = {r.post_id for r in reshares}
    for (
        post,
        user,  # Post author
        zone,
        era,
        likes_count,
        agree_count,
        disagree_count,
        comments_count,
    ) in paginated.items:
        user_reaction = user_reactions.get(post.id)
        is_bookmarked = post.id in bookmarked_posts
        is_reshared = post.id in user_reshared_posts

        data.append(
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "media": (post.media.split("|") if post.media else []),
                "created_at": post.created_at.isoformat(),
                "time_ago": time_ago(post.created_at),
                "pinned": post.pinned,
                "hot_thread": post.hot_thread,
                "likes_count": likes_count or 0,
                "agree_count": agree_count or 0,
                "disagree_count": disagree_count or 0,
                "user_agreed": user_reaction == "agree",
                "user_disagreed": user_reaction == "disagree",
                "comments_count": comments_count or 0,
                "bookmarked": is_bookmarked,  # Add bookmarked status
                "reshared": is_reshared,  # Add reshared status
                "author": {
                    "id": user.id,
                    "firstname": user.firstname,  # FIXED: Use post author's firstname
                    "lastname": user.lastname,  # FIXED: Use post author's lastname
                    "username": user.username,
                    "avatar": user.avatar or "",
                },
                "era": {
                    "id": era.id,
                    "name": era.name,
                    "year_range": era.year_range or "",
                },
                "zone": {"id": zone.id, "name": zone.name},
            }
        )

    return success_response(
        {"posts": data, "pagination": {"page": page, "total": paginated.total}},
        "Posts from your communities fetched",
    )


@community_bp.route("/posts/my-posts", methods=["GET"])
@token_required
def get_my_posts(current_user):
    """
    Get all posts created by the current user
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
        description: User's posts fetched successfully
        examples:
          application/json: {
            "success": true,
            "message": "Your posts fetched successfully",
            "data": {
              "posts": [
                {
                  "id": 1,
                  "title": "My Post Title",
                  "content": "My post content...",
                  "media": ["image1.jpg", "image2.jpg"],
                  "created_at": "2023-10-01T12:00:00",
                  "time_ago": "2 days ago",
                  "pinned": false,
                  "hot_thread": true,
                  "likes_count": 5,
                  "agree_count": 3,
                  "disagree_count": 2,
                  "user_agreed": false,
                  "user_disagreed": false,
                  "comments_count": 8,
                  "bookmarked": true,
                  "author": {
                    "id": 123,
                    "firstname": "John",
                    "lastname": "Doe",
                    "username": "johndoe",
                    "avatar": "avatar.jpg"
                  },
                  "era": {
                    "id": 1,
                    "name": "1980s",
                    "year_range": "1980-1989"
                  },
                  "zone": {
                    "id": 1,
                    "name": "Music"
                  }
                }
              ],
              "pagination": {
                "page": 1,
                "total": 15
              }
            }
          }
    """
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        print(f"🔍 DEBUG get_my_posts: Fetching posts for user_id={current_user.id}")

        # Query for posts created by the current user
        query = (
            db.session.query(
                Post,
                User,  # Post author (should be current user)
                Zone,
                Era,
                func.count(distinct(Like.id)).label("likes_count"),
                func.count(
                    distinct(case((Like.reaction_type == "agree", Like.id), else_=None))
                ).label("agree_count"),
                func.count(
                    distinct(case((Like.reaction_type == "disagree", Like.id), else_=None))
                ).label("disagree_count"),
                func.count(distinct(Comment.id)).label("comments_count"),
            )
            .join(User, Post.user_id == User.id)
            .join(Zone, Post.zone_id == Zone.id)
            .join(Era, Zone.era_id == Era.id)
            .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
            .outerjoin(Comment, Comment.post_id == Post.id)
            .filter(Post.user_id == current_user.id)  # Filter by current user's posts
            .group_by(Post.id, User.id, Zone.id, Era.id)
        )

        paginated = query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        print(f"🔍 DEBUG: Found {paginated.total} total posts by user, {len(paginated.items)} on this page")

        # Get user reactions and bookmarks for these posts
        user_reactions = {}
        bookmarked_posts = set()
        
        post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
        if post_ids:
            # Get user reactions (though user probably hasn't reacted to their own posts)
            reactions = Like.query.filter(
                Like.user_id == current_user.id,
                Like.post_id.in_(post_ids),
                Like.type == "post"
            ).all()
            user_reactions = {r.post_id: r.reaction_type for r in reactions}
            
            # Get bookmarked posts (user might bookmark their own posts)
            bookmarks = Bookmark.query.filter(
                Bookmark.user_id == current_user.id,
                Bookmark.post_id.in_(post_ids)
            ).all()
            bookmarked_posts = {bm.post_id for bm in bookmarks}

        data = []
        user_reshared_posts = set()
        if current_user:
            post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
            if post_ids:
                reshares = Reshare.query.filter(
                    Reshare.user_id == current_user.id,
                    Reshare.post_id.in_(post_ids)
                ).all()
                user_reshared_posts = {r.post_id for r in reshares}
        for (
            post,
            user,  # This should be the current user (post author)
            zone,
            era,
            likes_count,
            agree_count,
            disagree_count,
            comments_count,
        ) in paginated.items:
            user_reaction = user_reactions.get(post.id)
            is_bookmarked = post.id in bookmarked_posts
            is_reshared = post.id in user_reshared_posts

            data.append(
                {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "media": (post.media.split("|") if post.media else []),
                    "created_at": post.created_at.isoformat(),
                    "time_ago": time_ago(post.created_at),
                    "pinned": post.pinned,
                    "hot_thread": post.hot_thread,
                    "likes_count": likes_count or 0,
                    "agree_count": agree_count or 0,
                    "disagree_count": disagree_count or 0,
                    "user_agreed": user_reaction == "agree",
                    "user_disagreed": user_reaction == "disagree",
                    "comments_count": comments_count or 0,
                    "bookmarked": is_bookmarked,
                    "reshared": is_reshared,
                    
                    "author": {
                        "id": user.id,
                        "firstname": user.firstname,
                        "lastname": user.lastname,
                        "username": user.username,
                        "avatar": user.avatar or "",
                    },
                    "era": {
                        "id": era.id,
                        "name": era.name,
                        "year_range": era.year_range or "",
                    },
                    "zone": {"id": zone.id, "name": zone.name},
                }
            )

        print(f"✅ DEBUG: Successfully processed {len(data)} user posts")
        return success_response(
            {"posts": data, "pagination": {"page": page, "total": paginated.total}},
            "Your posts fetched successfully",
        )

    except Exception as e:
        print(f"❌ ERROR in get_my_posts: {str(e)}")
        import traceback
        print(f"❌ TRACEBACK:\n{traceback.format_exc()}")
        return error_response(f"Failed to fetch your posts: {str(e)}", 500)


@community_bp.route("/users/<int:user_id>/posts", methods=["GET"])
@token_required
def get_user_posts(current_user, user_id):
    """
    Get all posts created by a specific user
    ---
    tags:
      - Community
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID of the user whose posts to fetch
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
        description: User's posts fetched successfully
      404:
        description: User not found
    """
    try:
        # Check if user exists
        target_user = User.query.get(user_id)
        if not target_user:
            return error_response("User not found", 404)

        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)

        print(f"🔍 DEBUG get_user_posts: Fetching posts for user_id={user_id}")

        # Query for posts created by the target user
        query = (
            db.session.query(
                Post,
                User,  # Post author (the target user)
                Zone,
                Era,
                func.count(distinct(Like.id)).label("likes_count"),
                func.count(
                    distinct(case((Like.reaction_type == "agree", Like.id), else_=None))
                ).label("agree_count"),
                func.count(
                    distinct(case((Like.reaction_type == "disagree", Like.id), else_=None))
                ).label("disagree_count"),
                func.count(distinct(Comment.id)).label("comments_count"),
            )
            .join(User, Post.user_id == User.id)
            .join(Zone, Post.zone_id == Zone.id)
            .join(Era, Zone.era_id == Era.id)
            .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
            .outerjoin(Comment, Comment.post_id == Post.id)
            .filter(Post.user_id == user_id)  # Filter by target user's posts
            .group_by(Post.id, User.id, Zone.id, Era.id)
        )

        paginated = query.order_by(Post.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # Get current user's reactions and bookmarks for these posts
        user_reactions = {}
        bookmarked_posts = set()
        
        post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
        if post_ids and current_user:
            reactions = Like.query.filter(
                Like.user_id == current_user.id,
                Like.post_id.in_(post_ids),
                Like.type == "post"
            ).all()
            user_reactions = {r.post_id: r.reaction_type for r in reactions}
            
            bookmarks = Bookmark.query.filter(
                Bookmark.user_id == current_user.id,
                Bookmark.post_id.in_(post_ids)
            ).all()
            bookmarked_posts = {bm.post_id for bm in bookmarks}

        data = []
        user_reshared_posts = set()
        if current_user:
            post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
            if post_ids:
                reshares = Reshare.query.filter(
                    Reshare.user_id == current_user.id,
                    Reshare.post_id.in_(post_ids)
                ).all()
                user_reshared_posts = {r.post_id for r in reshares}
        for (
            post,
            user,  # The target user (post author)
            zone,
            era,
            likes_count,
            agree_count,
            disagree_count,
            comments_count,
        ) in paginated.items:
            user_reaction = user_reactions.get(post.id)
            is_bookmarked = post.id in bookmarked_posts if current_user else False
            user_reshared = post.id in user_reshared_posts if current_user else False

            data.append(
                {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "media": (post.media.split("|") if post.media else []),
                    "created_at": post.created_at.isoformat(),
                    "time_ago": time_ago(post.created_at),
                    "pinned": post.pinned,
                    "hot_thread": post.hot_thread,
                    "likes_count": likes_count or 0,
                    "agree_count": agree_count or 0,
                    "disagree_count": disagree_count or 0,
                    "user_agreed": user_reaction == "agree",
                    "user_disagreed": user_reaction == "disagree",
                    "comments_count": comments_count or 0,
                    "bookmarked": is_bookmarked,
                    "user_reshared": user_reshared,
                    "author": {
                        "id": user.id,
                        "firstname": user.firstname,
                        "lastname": user.lastname,
                        "username": user.username,
                        "avatar": user.avatar or "",
                    },
                    "era": {
                        "id": era.id,
                        "name": era.name,
                        "year_range": era.year_range or "",
                    },
                    "zone": {"id": zone.id, "name": zone.name},
                }
            )

        message = f"{target_user.username}'s posts fetched successfully"
        if user_id == current_user.id:
            message = "Your posts fetched successfully"

        return success_response(
            {"posts": data, "pagination": {"page": page, "total": paginated.total}},
            message,
        )

    except Exception as e:
        print(f"❌ ERROR in get_user_posts: {str(e)}")
        import traceback
        print(f"❌ TRACEBACK:\n{traceback.format_exc()}")
        return error_response(f"Failed to fetch user posts: {str(e)}", 500)


@community_bp.route("/posts/<int:post_id>", methods=["GET"])
@token_required
def get_single_post(current_user, post_id):
    """
    Get a single post by ID with full details
    ---
    tags:
      - Community
    parameters:
      - name: post_id
        in: path
        type: integer
        required: true
        description: ID of the post to retrieve
    responses:
      200:
        description: Post fetched successfully
      404:
        description: Post not found
    """
    # Query for the specific post with all counts and relationships
    result = (
        db.session.query(
            Post,
            User,
            Zone,
            Era,
            func.count(distinct(Like.id)).label("likes_count"),
            func.count(
                distinct(case((Like.reaction_type == "agree", Like.id), else_=None))
            ).label("agree_count"),
            func.count(
                distinct(case((Like.reaction_type == "disagree", Like.id), else_=None))
            ).label("disagree_count"),
            func.count(distinct(Comment.id)).label("comments_count"),
        )
        .join(User, Post.user_id == User.id)
        .join(Zone, Post.zone_id == Zone.id)
        .join(Era, Zone.era_id == Era.id)
        .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
        .outerjoin(Comment, Comment.post_id == Post.id)
        .filter(Post.id == post_id)
        .group_by(Post.id, User.id, Zone.id, Era.id)
        .first()
    )

    if not result:
        return error_response("Post not found", 404)

    # Unpack the result
    post, user, zone, era, likes_count, agree_count, disagree_count, comments_count = result

    # Get user's reaction to this post
    user_reaction = None
    if current_user:
        reaction = Like.query.filter(
            Like.user_id == current_user.id,
            Like.post_id == post_id,
            Like.type == "post"
        ).first()
        user_reaction = reaction.reaction_type if reaction else None

    # Check if post is bookmarked by current user
    is_bookmarked = False
    if current_user:
        bookmark = Bookmark.query.filter_by(
            user_id=current_user.id, 
            post_id=post_id
        ).first()
        is_bookmarked = bookmark is not None

    # Build the post data
    post_data = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "media": (post.media.split("|") if post.media else []),
        "created_at": post.created_at.isoformat(),
        "time_ago": time_ago(post.created_at),
        "pinned": post.pinned,
        "hot_thread": post.hot_thread,
        "likes_count": likes_count or 0,
        "agree_count": agree_count or 0,
        "disagree_count": disagree_count or 0,
        "user_agreed": user_reaction == "agree",
        "user_disagreed": user_reaction == "disagree",
        "comments_count": comments_count or 0,
        "bookmarked": is_bookmarked,
        "author": {
            "id": user.id,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "username": user.username,
            "avatar": user.avatar or "",
        },
        "era": {
            "id": era.id,
            "name": era.name,
            "year_range": era.year_range or "",
        },
        "zone": {
            "id": zone.id, 
            "name": zone.name
        },
    }

    return success_response(post_data, "Post fetched successfully")

# ---------------------------
# BOOKMARKS
# ---------------------------
@community_bp.route("/posts/<int:post_id>/bookmark", methods=["POST"])
@token_required
def toggle_bookmark(current_user, post_id):
    """
    Bookmark or unbookmark a post
    ---
    tags:
      - Bookmarks
    parameters:
      - name: post_id
        in: path
        type: integer
        required: true
        description: ID of the post to bookmark/unbookmark
    responses:
      201:
        description: Post bookmarked successfully
      200:
        description: Bookmark removed successfully
      404:
        description: Post not found
    """
    post = Post.query.get(post_id)
    if not post:
        return error_response("Post not found", 404)

    existing_bookmark = Bookmark.query.filter_by(
        user_id=current_user.id, post_id=post_id
    ).first()

    if existing_bookmark:
        db.session.delete(existing_bookmark)
        db.session.commit()
        return success_response(message="Bookmark removed")
    else:
        bookmark = Bookmark(user_id=current_user.id, post_id=post_id)
        db.session.add(bookmark)
        db.session.commit()
        return success_response(message="Post bookmarked", status=201)


@community_bp.route("/bookmarks", methods=["GET"])
@token_required
def get_bookmarks(current_user):
    """
    Get current user's bookmarked posts
    ---
    tags:
      - Bookmarks
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
        description: Bookmarked posts fetched successfully
        examples:
          application/json: {
            "success": true,
            "message": "Bookmarked posts fetched",
            "data": {
              "posts": [
                {
                  "id": 1,
                  "title": "Post Title",
                  "content": "Post content...",
                  "media": ["image1.jpg", "image2.jpg"],
                  "created_at": "2023-10-01T12:00:00",
                  "time_ago": "2 days ago",
                  "pinned": false,
                  "hot_thread": true,
                  "likes_count": 5,
                  "agree_count": 3,
                  "disagree_count": 2,
                  "user_agreed": true,
                  "user_disagreed": false,
                  "comments_count": 8,
                  "bookmarked": true,
                  "author": {
                    "id": 123,
                    "firstname": "John",
                    "lastname": "Doe",
                    "username": "johndoe",
                    "avatar": "avatar.jpg"
                  },
                  "era": {
                    "id": 1,
                    "name": "1980s",
                    "year_range": "1980-1989"
                  },
                  "zone": {
                    "id": 1,
                    "name": "Music"
                  }
                }
              ],
              "pagination": {
                "page": 1,
                "total": 50
              }
            }
          }
    """
    
    try:
        print(f"🔍 DEBUG get_bookmarks: Starting for user_id={current_user.id}")
        
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        
        print(f"🔍 DEBUG: page={page}, per_page={per_page}")

        # Option 1: Include Bookmark in the GROUP BY clause
        query = (
            db.session.query(
                Post,
                User,
                Zone,
                Era,
                Bookmark,  # Add Bookmark to the query
                func.count(distinct(Like.id)).label("likes_count"),
                func.count(
                    distinct(case((Like.reaction_type == "agree", Like.id), else_=None))
                ).label("agree_count"),
                func.count(
                    distinct(case((Like.reaction_type == "disagree", Like.id), else_=None))
                ).label("disagree_count"),
                func.count(distinct(Comment.id)).label("comments_count"),
            )
            .join(Bookmark, Bookmark.post_id == Post.id)
            .join(User, Post.user_id == User.id)
            .join(Zone, Post.zone_id == Zone.id)
            .join(Era, Zone.era_id == Era.id)
            .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
            .outerjoin(Comment, Comment.post_id == Post.id)
            .filter(Bookmark.user_id == current_user.id)
            .group_by(Post.id, User.id, Zone.id, Era.id, Bookmark.id)  # Add Bookmark.id to GROUP BY
        )

        print("🔍 DEBUG: Executing paginated query...")
        paginated = query.order_by(Bookmark.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        print(f"🔍 DEBUG: Found {paginated.total} total bookmarks, {len(paginated.items)} on this page")

        # Get user reactions for bookmarked posts
        user_reactions = {}
        post_ids = [post.id for post, _, _, _, _, _, _, _, _ in paginated.items]  # Updated unpacking
        print(f"🔍 DEBUG: Post IDs to check reactions for: {post_ids}")
        
        if post_ids:
            reactions = Like.query.filter(
                Like.user_id == current_user.id,
                Like.post_id.in_(post_ids),
                Like.type == "post"
            ).all()
            user_reactions = {r.post_id: r.reaction_type for r in reactions}
            print(f"🔍 DEBUG: User reactions found: {user_reactions}")

        data = []
        # Updated unpacking to include Bookmark
        for post, user, zone, era, bookmark, likes_count, agree_count, disagree_count, comments_count in paginated.items:
            user_reaction = user_reactions.get(post.id)
            
            print(f"🔍 DEBUG: Processing post {post.id} - {post.title}")

            data.append(
                {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "media": (post.media.split("|") if post.media else []),
                    "created_at": post.created_at.isoformat(),
                    "time_ago": time_ago(post.created_at),
                    "pinned": post.pinned,
                    "hot_thread": post.hot_thread,
                    "likes_count": likes_count or 0,
                    "agree_count": agree_count or 0,
                    "disagree_count": disagree_count or 0,
                    "user_agreed": user_reaction == "agree",
                    "user_disagreed": user_reaction == "disagree",
                    "comments_count": comments_count or 0,
                    "bookmarked": True,
                    "bookmarked_at": bookmark.created_at.isoformat(),  # Optional: include bookmark timestamp
                    "author": {
                        "id": user.id,
                        "firstname": user.firstname,
                        "lastname": user.lastname,
                        "username": user.username,
                        "avatar": user.avatar or "",
                    },
                    "era": {
                        "id": era.id,
                        "name": era.name,
                        "year_range": era.year_range or "",
                    },
                    "zone": {"id": zone.id, "name": zone.name},
                }
            )

        print(f"✅ DEBUG: Successfully processed {len(data)} posts")
        return success_response(
            {"posts": data, "pagination": {"page": page, "total": paginated.total}},
            "Bookmarked posts fetched",
        )

    except Exception as e:
        print(f"❌ ERROR in get_bookmarks: {str(e)}")
        import traceback
        print(f"❌ TRACEBACK:\n{traceback.format_exc()}")
        return error_response(f"Internal server error: {str(e)}", 500)


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

    query = (
        db.session.query(
            Post,
            User,  # This is the post author
            Zone,
            Era,
            func.count(distinct(Like.id)).label("likes_count"),
            func.count(
                distinct(case((Like.reaction_type == "agree", Like.id), else_=None))
            ).label("agree_count"),
            func.count(
                distinct(case((Like.reaction_type == "disagree", Like.id), else_=None))
            ).label("disagree_count"),
            func.count(distinct(Comment.id)).label("comments_count"),
        )
        .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
        .outerjoin(Comment, Comment.post_id == Post.id)
        .join(User, Post.user_id == User.id)  # Join with User to get author info
        .join(Zone, Post.zone_id == Zone.id)
        .join(Era, Zone.era_id == Era.id)
        .group_by(Post.id, User.id, Zone.id, Era.id)
    )

    paginated = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    user_reactions = {}
    bookmarked_posts = set()

    if current_user:
        post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
        if post_ids:
            # Get user reactions
            reactions = Like.query.filter(
                Like.user_id == current_user.id,
                Like.post_id.in_(post_ids),
                Like.type == "post",
            ).all()
            user_reactions = {r.post_id: r.reaction_type for r in reactions}

            # Get bookmarked posts
            bookmarks = Bookmark.query.filter(
                Bookmark.user_id == current_user.id,
                Bookmark.post_id.in_(post_ids)
            ).all()
            bookmarked_posts = {bm.post_id for bm in bookmarks}

    data = []
    user_reshared_posts = set()
    if current_user:
        post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
        if post_ids:
            reshares = Reshare.query.filter(
                Reshare.user_id == current_user.id, Reshare.post_id.in_(post_ids)
            ).all()
            user_reshared_posts = {r.post_id for r in reshares}
    for (
        post,
        user,  # This is the post author
        zone,
        era,
        likes_count,
        agree_count,
        disagree_count,
        comments_count,
    ) in paginated.items:
        user_reaction = user_reactions.get(post.id)
        is_bookmarked = post.id in bookmarked_posts if current_user else False
        user_reshared = post.id in user_reshared_posts if current_user else False

        data.append(
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "media": (post.media.split("|") if post.media else []),
                "created_at": post.created_at.isoformat(),
                "time_ago": time_ago(post.created_at),
                "pinned": post.pinned,
                "hot_thread": post.hot_thread,
                "likes_count": likes_count or 0,
                "agree_count": agree_count or 0,
                "disagree_count": disagree_count or 0,
                "user_agreed": user_reaction == "agree",
                "user_disagreed": user_reaction == "disagree",
                "comments_count": comments_count or 0,
                "bookmarked": is_bookmarked,  # Add bookmarked status
                "user_reshared": user_reshared,  # Add reshared status
                "author": {
                    "id": user.id,  # Use post author's ID
                    "firstname": user.firstname,  # FIXED: Use post author's firstname
                    "lastname": user.lastname,    # FIXED: Use post author's lastname
                    "username": user.username,    # This was already correct
                    "avatar": user.avatar or "",
                },
                "era": {
                    "id": era.id,
                    "name": era.name,
                    "year_range": era.year_range or "",
                },
                "zone": {"id": zone.id, "name": zone.name},
            }
        )

    return success_response(
        {"posts": data, "pagination": {"page": page, "total": paginated.total}},
        "All posts fetched",
    )


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
            User,  # Post author
            Zone,
            Era,
            func.count(distinct(Like.id)).label("likes_count"),
            func.count(
                distinct(case((Like.reaction_type == "agree", Like.id), else_=None))
            ).label("agree_count"),
            func.count(
                distinct(case((Like.reaction_type == "disagree", Like.id), else_=None))
            ).label("disagree_count"),
            func.count(distinct(Comment.id)).label("comments_count"),
        )
        .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
        .outerjoin(Comment, Comment.post_id == Post.id)
        .join(User, Post.user_id == User.id)  # Join with User to get author
        .join(Zone, Post.zone_id == Zone.id)
        .join(Era, Zone.era_id == Era.id)
        .group_by(Post.id, User.id, Zone.id, Era.id)
    )

    # If no era_id specified, default to user's communities
    # if not era_id and current_user:
    #     user_era_ids = [era.id for era in current_user.joined_eras]
    #     if user_era_ids:
    #         query = query.filter(Era.id.in_(user_era_ids))

    if era_id:
        query = query.filter(Era.id == era_id)

    paginated = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    user_reactions = {}
    bookmarked_posts = set()

    if current_user:
        post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
        if post_ids:
            # Get user reactions
            reactions = Like.query.filter(
                Like.user_id == current_user.id,
                Like.post_id.in_(post_ids),
                Like.type == "post",
            ).all()
            user_reactions = {r.post_id: r.reaction_type for r in reactions}

            # Get bookmarked posts
            bookmarks = Bookmark.query.filter(
                Bookmark.user_id == current_user.id,
                Bookmark.post_id.in_(post_ids)
            ).all()
            bookmarked_posts = {bm.post_id for bm in bookmarks}

    data = []
    user_reshared_posts = set()
    if current_user:
        post_ids = [post.id for post, _, _, _, _, _, _, _ in paginated.items]
        if post_ids:
            reshares = Reshare.query.filter(
                Reshare.user_id == current_user.id, Reshare.post_id.in_(post_ids)
            ).all()
            user_reshared_posts = {r.post_id for r in reshares}
    for (
        post,
        user,  # Post author
        zone,
        era,
        likes_count,
        agree_count,
        disagree_count,
        comments_count,
    ) in paginated.items:
        user_reaction = user_reactions.get(post.id)
        is_bookmarked = post.id in bookmarked_posts if current_user else False
        user_reshared = post.id in user_reshared_posts if current_user else False

        data.append(
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "media": (post.media.split("|") if post.media else []),
                "created_at": post.created_at.isoformat(),
                "time_ago": time_ago(post.created_at),
                "pinned": post.pinned,
                "hot_thread": post.hot_thread,
                "likes_count": likes_count or 0,
                "agree_count": agree_count or 0,
                "disagree_count": disagree_count or 0,
                "user_agreed": user_reaction == "agree",
                "user_disagreed": user_reaction == "disagree",
                "comments_count": comments_count or 0,
                "bookmarked": is_bookmarked,  # Add bookmarked status
                "user_reshared": user_reshared,  # Add reshared status
                "author": {
                    "id": user.id,
                    "firstname": user.firstname,  # FIXED: Use post author's firstname
                    "lastname": user.lastname,    # FIXED: Use post author's lastname
                    "username": user.username,
                    "avatar": user.avatar or "",
                },
                "era": {
                    "id": era.id,
                    "name": era.name,
                    "year_range": era.year_range or "",
                },
                "zone": {"id": zone.id, "name": zone.name},
            }
        )
    return success_response(
        {"posts": data, "pagination": {"page": page, "total": paginated.total}},
        "Posts fetched",
    )


# @community_bp.route("/posts/<int:post_id>", methods=["DELETE"])
# @token_required
# def delete_post(current_user, post_id):
#     """
#     Delete a post (Admin or Post Owner only)
#     ---
#     tags:
#       - Community
#     parameters:
#       - in: path
#         name: post_id
#         required: true
#         schema:
#           type: integer
#     responses:
#       200:
#         description: Post deleted successfully
#       401:
#         description: Unauthorized
#       403:
#         description: Forbidden - Not authorized to delete this post
#       404:
#         description: Post not found
#     """
#     try:
#         post = Post.query.get(post_id)
#         if not post:
#             return error_response("Post not found", 404)

#         # Check if user is either admin OR the post owner
#         is_admin = hasattr(current_user, "role") and current_user.role == "admin"
#         is_owner = post.user_id == current_user.id

#         if not (is_admin or is_owner):
#             return error_response("You are not authorized to delete this post", 403)

#         # Store post info for the socket event before deletion
#         post_info = {"id": post.id, "title": post.title, "author_id": post.user_id}

#         db.session.delete(post)
#         db.session.commit()

#         # 🔴 Emit real-time event
#         socketio.emit(
#             "post_deleted",
#             {"id": post_id, "deleted_by": current_user.id, "was_admin": is_admin},
#             broadcast=True,
#         )

#         return success_response(message="Post deleted successfully")

#     except Exception as e:
#         print(f"❌ ERROR in delete_post: {str(e)}")
#         db.session.rollback()
#         return error_response("Failed to delete post", 500)


@community_bp.route("/posts/<int:post_id>", methods=["DELETE"])
@token_required
def delete_post(current_user, post_id):
    """
    Delete a post (Admin or Post Owner only)
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
        description: Forbidden - Not authorized to delete this post
      404:
        description: Post not found
    """
    try:
        print(
            f"🔍 DEBUG delete_post: Starting deletion for post_id={post_id}, user_id={current_user.id}"
        )

        post = Post.query.get(post_id)
        if not post:
            print(f"❌ DEBUG: Post {post_id} not found")
            return error_response("Post not found", 404)

        # Check if user is either admin OR the post owner
        is_admin = hasattr(current_user, "role") and current_user.role == "admin"
        is_owner = post.user_id == current_user.id

        print(
            f"🔍 DEBUG: is_admin={is_admin}, is_owner={is_owner}, post.user_id={post.user_id}, current_user.id={current_user.id}"
        )

        if not (is_admin or is_owner):
            return error_response("You are not authorized to delete this post", 403)

        # Store post info for the socket event before deletion
        post_info = {"id": post.id, "title": post.title, "author_id": post.user_id}

        # 🔴 FIRST: Delete all related records to avoid foreign key constraints
        try:
            print("🔍 DEBUG: Deleting related comments...")
            # Delete comments on this post
            Comment.query.filter_by(post_id=post_id).delete()

            print("🔍 DEBUG: Deleting related likes...")
            # Delete likes on this post
            Like.query.filter_by(post_id=post_id, type="post").delete()

            print("🔍 DEBUG: Deleting related bookmarks...")
            # Delete bookmarks for this post
            Bookmark.query.filter_by(post_id=post_id).delete()

            print("🔍 DEBUG: Deleting related reshares...")
            # Delete reshare records for this post
            Reshare.query.filter_by(post_id=post_id).delete()

            # If you have any other related tables, add them here

            print("🔍 DEBUG: All related records deleted, now deleting post...")

        except Exception as related_error:
            print(f"❌ DEBUG: Error deleting related records: {str(related_error)}")
            db.session.rollback()
            return error_response("Failed to clean up post dependencies", 500)

        # Now delete the post
        db.session.delete(post)
        db.session.commit()

        print("✅ DEBUG: Post deleted successfully")

        # 🔴 Emit real-time event
        socketio.emit(
            "post_deleted",
            {"id": post_id, "deleted_by": current_user.id, "was_admin": is_admin},
            broadcast=True,
        )

        return success_response(message="Post deleted successfully")

    except Exception as e:
        print(f"❌ ERROR in delete_post: {str(e)}")
        import traceback

        print(f"❌ TRACEBACK:\n{traceback.format_exc()}")
        db.session.rollback()
        return error_response(f"Failed to delete post: {str(e)}", 500)


# ---------------------------
# COMMENTS
# ---------------------------

@community_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
@token_required
def add_comment(current_user, post_id):
    """
    Add a comment to a post or reply to an existing comment
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
            parent_comment_id: {type: integer, description: "ID of parent comment for replies"}
    responses:
      201:
        description: Comment added successfully
      400:
        description: Content is required
      401:
        description: Unauthorized
      404:
        description: Post not found or Parent comment not found
    """
    data = request.get_json()
    if not data.get("content"):
        return error_response("Content is required", 400)

    post = Post.query.get(post_id)
    if not post:
        return error_response("Post not found", 404)

    parent_comment_id = data.get("parent_comment_id")
    
    # Validate parent comment if provided
    if parent_comment_id:
        parent_comment = Comment.query.filter_by(
            id=parent_comment_id, 
            post_id=post_id
        ).first()
        if not parent_comment:
            return error_response("Parent comment not found", 404)

    comment = Comment(
        content=data["content"], 
        user_id=current_user.id, 
        post_id=post_id,
        parent_comment_id=parent_comment_id
    )
    db.session.add(comment)
    db.session.commit()

    # Get the author info for the response
    user = User.query.get(current_user.id)

    comment_data = {
        "id": comment.id,
        "content": comment.content,
        "created_at": comment.created_at.isoformat(),
        "time_ago": time_ago(comment.created_at),
        "parent_comment_id": comment.parent_comment_id,
        "author": {
            "id": user.id,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "username": user.username,
            "avatar": user.avatar or "",
        },
    }

    # 🔴 Emit real-time event
    socketio.emit(
        "comment_added",
        {
            **comment_data,
            "post_id": comment.post_id,
        },
        # broadcast=True,
    )

    return success_response(
        {"comment": comment_data},
        "Comment added successfully",
        status=201,
    )


@community_bp.route("/comments/<int:comment_id>/replies", methods=["GET"])
@token_required
def get_comment_replies(current_user, comment_id):
    """
    Get all replies for a specific comment
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: comment_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Comment replies fetched successfully
      404:
        description: Comment not found
    """
    parent_comment = Comment.query.get(comment_id)
    if not parent_comment:
        return error_response("Comment not found", 404)

    replies = (
        Comment.query.filter_by(parent_comment_id=comment_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    data = []
    for reply in replies:
        user = User.query.get(reply.user_id)
        data.append(
            {
                "id": reply.id,
                "content": reply.content,
                "created_at": reply.created_at.isoformat(),
                "time_ago": time_ago(reply.created_at),
                "author": {
                    "id": user.id,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "username": user.username,
                    "avatar": user.avatar or "",
                },
            }
        )

    return success_response(data, "Comment replies fetched successfully")


@community_bp.route("/comments/<int:comment_id>/thread", methods=["GET"])
@token_required
def get_comment_thread(current_user, comment_id):
    """
    Get a complete comment thread starting from a specific comment
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: comment_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Comment thread fetched successfully
      404:
        description: Comment not found
    """
    def get_comment_with_ancestors(comment_id):
        """Get comment and all its ancestors"""
        comment = Comment.query.get(comment_id)
        if not comment:
            return None
            
        user = User.query.get(comment.user_id)
        comment_data = {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "time_ago": time_ago(comment.created_at),
            "author": {
                "id": user.id,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "username": user.username,
                "avatar": user.avatar or "",
            },
            "replies": []
        }
        
        # If this comment has a parent, get the parent chain
        if comment.parent_comment_id:
            parent_data = get_comment_with_ancestors(comment.parent_comment_id)
            if parent_data:
                comment_data["parent"] = parent_data
        
        return comment_data

    def get_comment_with_descendants(comment_id):
        """Get comment and all its replies recursively"""
        comment = Comment.query.get(comment_id)
        if not comment:
            return None
            
        user = User.query.get(comment.user_id)
        comment_data = {
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "time_ago": time_ago(comment.created_at),
            "author": {
                "id": user.id,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "username": user.username,
                "avatar": user.avatar or "",
            },
            "replies": []
        }
        
        # Get all direct replies
        replies = Comment.query.filter_by(parent_comment_id=comment_id)\
                              .order_by(Comment.created_at.asc())\
                              .all()
        
        for reply in replies:
            comment_data["replies"].append(get_comment_with_descendants(reply.id))
            
        return comment_data

    # Get the complete thread
    thread_data = get_comment_with_descendants(comment_id)
    if not thread_data:
        return error_response("Comment not found", 404)

    return success_response(thread_data, "Comment thread fetched successfully")

@community_bp.route("/posts/<int:post_id>/reshare", methods=["POST"])
@token_required
def reshare_post(current_user, post_id):
    """
    Reshare a post (increment reshare counter)
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
        description: Post reshared successfully
      400:
        description: Already reshared this post
      404:
        description: Post not found
    """
    try:
        # Get the post
        post = Post.query.get(post_id)
        if not post:
            return error_response("Post not found", 404)
        
        # Check if user already reshared this post
        existing_reshare = Reshare.query.filter_by(
            user_id=current_user.id,
            post_id=post_id
        ).first()
        
        if existing_reshare:
            return error_response("You have already reshared this post", 400)
        
        # Create reshare record
        reshare = Reshare(user_id=current_user.id, post_id=post_id)
        db.session.add(reshare)
        
        # Increment reshare counter
        post.reshare_count += 1
        
        db.session.commit()
        
        # 🔴 Emit real-time event
        socketio.emit(
            "post_reshared",
            {
                "post_id": post_id,
                "reshare_count": post.reshare_count,
                "reshared_by": current_user.id,
                "reshared_by_username": current_user.username
            },
            broadcast=True
        )
        
        return success_response(
            {
                "reshare_count": post.reshare_count,
                "user_reshared": True
            },
            "Post reshared successfully"
        )
        
    except Exception as e:
        print(f"❌ ERROR in reshare_post: {str(e)}")
        db.session.rollback()
        return error_response(f"Failed to reshare post: {str(e)}", 500)


@community_bp.route("/posts/<int:post_id>/unreshare", methods=["POST"])
@token_required
def unreshare_post(current_user, post_id):
    """
    Remove reshare from a post (decrement reshare counter)
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
        description: Reshare removed successfully
      404:
        description: Reshare not found or Post not found
    """
    try:
        # Get the post
        post = Post.query.get(post_id)
        if not post:
            return error_response("Post not found", 404)

        # Find the reshare record
        reshare = Reshare.query.filter_by(
            user_id=current_user.id,
            post_id=post_id
        ).first()

        if not reshare:
            return error_response("You have not reshared this post", 404)

        # Remove reshare record
        db.session.delete(reshare)

        # Decrement reshare counter (ensure it doesn't go below 0)
        post.reshare_count = max(0, post.reshare_count - 1)

        db.session.commit()

        # 🔴 Emit real-time event
        socketio.emit(
            "post_unreshared",
            {
                "post_id": post_id,
                "reshare_count": post.reshare_count,
                "unreshared_by": current_user.id
            },
            broadcast=True
        )

        return success_response(
            {
                "reshare_count": post.reshare_count,
                "user_reshared": False
            },
            "Reshare removed successfully"
        )

    except Exception as e:
        print(f"❌ ERROR in unreshare_post: {str(e)}")
        db.session.rollback()
        return error_response(f"Failed to remove reshare: {str(e)}", 500)


@community_bp.route("/posts/<int:post_id>/reshare/status", methods=["GET"])
@token_required
def get_reshare_status(current_user, post_id):
    """
    Check if current user has reshared a post
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
        description: Reshare status fetched successfully
      404:
        description: Post not found
    """
    post = Post.query.get(post_id)
    if not post:
        return error_response("Post not found", 404)

    has_reshared = (
        Reshare.query.filter_by(user_id=current_user.id, post_id=post_id).first()
        is not NoneReshare # type: ignore
    )

    return success_response(
        {"user_reshared": has_reshared, "reshare_count": post.reshare_count},
        "Reshare status fetched successfully",
    )


@community_bp.route("/posts/<int:post_id>/reshares/users", methods=["GET"])
@token_required
def get_reshare_users(current_user, post_id):
    """
    Get users who reshared a specific post
    ---
    tags:
      - Community
    parameters:
      - in: path
        name: post_id
        required: true
        schema:
          type: integer
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
        description: Reshare users fetched successfully
      404:
        description: Post not found
    """
    post = Post.query.get(post_id)
    if not post:
        return error_response("Post not found", 404)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    reshares = (
        Reshare.query.filter_by(post_id=post_id)
        .order_by(Reshare.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    data = []
    for reshare in reshares.items:
        user = User.query.get(reshare.user_id)
        data.append(
            {
                "id": user.id,
                "firstname": user.firstname,
                "lastname": user.lastname,
                "username": user.username,
                "avatar": user.avatar or "",
                "reshared_at": reshare.created_at.isoformat(),
                "time_ago": time_ago(reshare.created_at),
            }
        )

    return success_response(
        {"users": data, "pagination": {"page": page, "total": reshares.total}},
        "Reshare users fetched successfully",
    )


# @community_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
# @token_required
# def add_comment(current_user, post_id):
#     """
#     Add a comment to a post
#     ---
#     tags:
#       - Community
#     parameters:
#       - in: path
#         name: post_id
#         required: true
#         schema:
#           type: integeri
#       - in: body
#         name: body
#         schema:
#           type: object
#           required: [content]
#           properties:
#             content: {type: string}
#     responses:
#       201:
#         description: Comment added successfully
#       400:
#         description: Content is required
#       401:
#         description: Unauthorized
#       404:
#         description: Post not found
#     """
#     data = request.get_json()
#     if not data.get("content"):
#         return error_response("Content is required", 400)

#     post = Post.query.get(post_id)
#     if not post:
#         return error_response("Post not found", 404)

#     comment = Comment(content=data["content"], user_id=current_user.id, post_id=post_id)
#     db.session.add(comment)
#     db.session.commit()

#     # 🔴 Emit real-time event
#     socketio.emit(
#         "comment_added",
#         {
#             "id": comment.id,
#             "content": comment.content,
#             "created_at": comment.created_at.isoformat(),
#             "time_ago": time_ago(comment.created_at),
#             "user_id": comment.user_id,
#             "post_id": comment.post_id,
#             "author": {
#                 "id": current_user.id,
#                 "firstname": current_user.firstname,
#                 "lastname": current_user.lastname,
#                 "username": current_user.username,
#                 "avatar": current_user.avatar or "",
#             },
#         },
#         # broadcast=True,
#     )

#     # return success_response(message="Comment added successfully", status=201)
#     return success_response(
#         {
#             "comment": {
#                 "id": comment.id,
#                 "content": comment.content,
#                 "created_at": comment.created_at.isoformat(),
#                 "time_ago": time_ago(comment.created_at),
#                 "author": {
#                     "id": current_user.id,
#                     "firstname": current_user.firstname,
#                     "lastname": current_user.lastname,
#                     "username": current_user.username,
#                     "avatar": current_user.avatar or "",
#                 },
#             }
#         },
#         "Comment added successfully",
#         status=201,
#     )


# ---------------------------
# REACTIONS (Agree/Dislike)
# ---------------------------
@community_bp.route("/posts/<int:post_id>/agree", methods=["POST"])
@token_required
def add_agree(current_user, post_id):
    """
    Add agree reaction to a post
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
        description: Agree added
      200:
        description: Agree removed
      401:
        description: Unauthorized
      404:
        description: Post not found
    """
    return _handle_reaction(current_user, post_id, "agree")


@community_bp.route("/posts/<int:post_id>/disagree", methods=["POST"])
@token_required
def add_disagree(current_user, post_id):
    """
    Add disagree reaction to a post
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
        description: Disagree added
      200:
        description: Disagree removed
      401:
        description: Unauthorized
      404:
        description: Post not found
    """
    return _handle_reaction(current_user, post_id, "disagree")


def _handle_reaction(current_user, post_id, reaction_type):
    """
    Helper function to handle agree/disagree reactions
    """
    # Check if post exists
    post = Post.query.get(post_id)
    if not post:
        return error_response("Post not found", 404)

    # Check for existing reaction of any type by this user
    existing_reaction = Like.query.filter_by(
        user_id=current_user.id, post_id=post_id, type="post"
    ).first()

    if existing_reaction:
        if existing_reaction.reaction_type == reaction_type:
            # User is clicking the same button - remove the reaction
            db.session.delete(existing_reaction)
            db.session.commit()

            # Emit reaction removed event
            socketio.emit(
                f"post_{reaction_type}_removed",
                {
                    "post_id": post_id,
                    "user_id": current_user.id,
                    "reaction_type": reaction_type,
                },
                # broadcast=True,
            )

            return success_response(message=f"{reaction_type.capitalize()} removed")
        else:
            # User is switching reaction types - update existing reaction
            existing_reaction.reaction_type = reaction_type
            db.session.commit()

            # Emit reaction changed event
            socketio.emit(
                f"post_reaction_changed",
                {
                    "post_id": post_id,
                    "user_id": current_user.id,
                    "old_reaction_type": existing_reaction.reaction_type,
                    "new_reaction_type": reaction_type,
                },
                broadcast=True,
            )

            return success_response(message=f"Reaction changed to {reaction_type}")
    else:
        # Create new reaction
        reaction = Like(
            user_id=current_user.id,
            post_id=post_id,
            type="post",
            reaction_type=reaction_type,
        )
        db.session.add(reaction)
        db.session.commit()

        # Emit new reaction event
        socketio.emit(
            f"post_{reaction_type}_added",
            {
                "post_id": post_id,
                "user_id": current_user.id,
                "reaction_type": reaction_type,
            },
            broadcast=True,
        )

        return success_response(
            message=f"{reaction_type.capitalize()} added", status=201
        )


# ---------------------------
# GET REACTION COUNTS
# ---------------------------
@community_bp.route("/posts/<int:post_id>/reactions", methods=["GET"])
def get_post_reactions(post_id):
    """
    Get agree/disagree counts for a post
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
        description: Reaction counts retrieved
      404:
        description: Post not found
    """
    post = Post.query.get(post_id)
    if not post:
        return error_response("Post not found", 404)

    agree_count = Like.query.filter_by(
        post_id=post_id, type="post", reaction_type="agree"
    ).count()

    disagree_count = Like.query.filter_by(
        post_id=post_id, type="post", reaction_type="disagree"
    ).count()

    return success_response(
        {
            "post_id": post_id,
            "agree_count": agree_count,
            "disagree_count": disagree_count,
        },
        "Reaction counts retrieved",
    )


# ---------------------------
# GET USER REACTION STATUS
# ---------------------------
@community_bp.route("/posts/<int:post_id>/my-reaction", methods=["GET"])
@token_required
def get_my_reaction(current_user, post_id):
    """
    Get current user's reaction to a post
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
        description: User reaction status
      404:
        description: Post not found
    """
    post = Post.query.get(post_id)
    if not post:
        return error_response("Post not found", 404)

    my_reaction = Like.query.filter_by(
        user_id=current_user.id, post_id=post_id, type="post"
    ).first()

    reaction_data = {
        "post_id": post_id,
        "user_reacted": my_reaction is not None,
        "reaction_type": my_reaction.reaction_type if my_reaction else None,
    }

    return success_response(reaction_data, "User reaction status retrieved")


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
def get_zone_posts(current_user=None, zone_id=None):
    """
    Get all posts in a specific zone with full details (same shape as all other feeds)
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Verify zone exists
    zone = Zone.query.get_or_404(zone_id)

    # Main query — identical structure to all other post endpoints
    query = (
        db.session.query(
            Post,
            User,  # author
            Zone,
            Era,
            func.count(distinct(Like.id)).label("likes_count"),
            func.count(distinct(case((Like.reaction_type == "agree", Like.id)))).label(
                "agree_count"
            ),
            func.count(
                distinct(case((Like.reaction_type == "disagree", Like.id)))
            ).label("disagree_count"),
            func.count(distinct(Comment.id)).label("comments_count"),
        )
        .join(User, Post.user_id == User.id)
        .join(Zone, Post.zone_id == Zone.id)
        .join(Era, Zone.era_id == Era.id)
        .outerjoin(Like, (Like.post_id == Post.id) & (Like.type == "post"))
        .outerjoin(Comment, Comment.post_id == Post.id)
        .filter(Post.zone_id == zone_id)
        .group_by(Post.id, User.id, Zone.id, Era.id)
    )

    paginated = query.order_by(Post.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Get current user's reactions, bookmarks, and reshares
    post_ids = [p.id for p, _, _, _, _, _, _, _ in paginated.items]

    user_reactions = {}
    bookmarked_posts = set()
    user_reshared_posts = set()

    if current_user and post_ids:
        # Reactions
        reactions = Like.query.filter(
            Like.user_id == current_user.id,
            Like.post_id.in_(post_ids),
            Like.type == "post",
        ).all()
        user_reactions = {r.post_id: r.reaction_type for r in reactions}

        # Bookmarks
        bookmarks = Bookmark.query.filter(
            Bookmark.user_id == current_user.id, Bookmark.post_id.in_(post_ids)
        ).all()
        bookmarked_posts = {b.post_id for b in bookmarks}

        # Reshares — FIXED: parentheses now closed!
        reshares = Reshare.query.filter(
            Reshare.user_id == current_user.id, Reshare.post_id.in_(post_ids)
        ).all()
        user_reshared_posts = {r.post_id for r in reshares}

    # Build response data
    data = []
    for (
        post,
        user,
        zone,
        era,
        likes_count,
        agree_count,
        disagree_count,
        comments_count,
    ) in paginated.items:
        data.append(
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "media": post.media.split("|") if post.media else [],
                "created_at": post.created_at.isoformat(),
                "time_ago": time_ago(post.created_at),
                "pinned": post.pinned,
                "hot_thread": post.hot_thread,
                "likes_count": likes_count or 0,
                "agree_count": agree_count or 0,
                "disagree_count": disagree_count or 0,
                "comments_count": comments_count or 0,
                "user_agreed": user_reactions.get(post.id) == "agree",
                "user_disagreed": user_reactions.get(post.id) == "disagree",
                "bookmarked": post.id in bookmarked_posts,
                "reshared": post.id in user_reshared_posts,
                "author": {
                    "id": user.id,
                    "firstname": user.firstname,
                    "lastname": user.lastname,
                    "username": user.username,
                    "avatar": user.avatar or "",
                },
                "era": {
                    "id": era.id,
                    "name": era.name,
                    "year_range": era.year_range or "",
                },
                "zone": {"id": zone.id, "name": zone.name},
            }
        )

    return success_response(
        {
            "posts": data,
            "pagination": {
                "page": page,
                "total": paginated.total,
                "pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev,
            },
        },
        f"Posts from {zone.name} fetched successfully",
    )


# @community_bp.route("/<int:zone_id>/posts", methods=["GET"])
# @token_required
# def get_community_posts(current_user, zone_id):
#     """
#     Get posts in a community zone
#     ---
#     tags:
#       - Community
#     parameters:
#       - in: path
#         name: zone_id
#         required: true
#         schema:
#           type: integer
#     responses:
#       200:
#         description: Community posts fetched successfully
#       401:
#         description: Unauthorized
#       404:
#         description: Community not found
#     """
#     zone = Zone.query.get(zone_id)
#     if not zone:
#         return error_response("Community not found", 404)

#     posts = Post.query.filter_by(zone_id=zone.id).all()
#     data = [
#         {
#             "id": p.id,
#             "title": p.title,
#             "content": p.content,
#             "pinned": p.pinned,
#             "hot_thread": p.hot_thread,
#             "created_at": p.created_at.isoformat(),
#             "user_id": p.user_id,
#         }
#         for p in posts
#     ]
#     return success_response(data, "Community posts fetched successfully")


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
