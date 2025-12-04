# app/utils/decorators.py
from functools import wraps
from flask import request, current_app
import jwt
from app.utils.responses import error_response
from sqlalchemy import text
from app import db  # Import db directly from app package
from app.models import User

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
            elif len(parts) == 1:
                token = parts[0]  # fallback for token without "Bearer "

        if not token:
            return error_response("Token is missing!", 401)

        try:
            data = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            user_id = data.get("id") or data.get("user_id") or data.get("sub")

            if not user_id:
                return error_response("Invalid token: no user identifier", 401)

            current_user = User.query.get(user_id)
            if not current_user:
                return error_response("User not found", 404)

        except jwt.ExpiredSignatureError:
            return error_response("Token has expired!", 401)
        except jwt.InvalidTokenError:
            return error_response("Invalid token!", 401)
        except Exception as e:
            current_app.logger.error(f"Token auth error: {e}")
            return error_response("Authentication failed", 401)

        # Only authenticated users reach here
        return f(current_user, *args, **kwargs)

    return decorated


# def token_required(f):
#     @wraps(f)
#     def decorated(*args, **kwargs):
#         token = None

#         # Get token from Authorization header
#         if "Authorization" in request.headers:
#             auth_header = request.headers["Authorization"]
#             if auth_header.startswith("Bearer "):
#                 token = auth_header.split(" ")[1]
#             else:
#                 # Try without Bearer prefix
#                 token = auth_header

#         # Debug: Log token presence
#         print(f"🔐 DEBUG: Token present: {token is not None}")
#         if token:
#             print(f"🔐 DEBUG: Token length: {len(token)}")
#             print(f"🔐 DEBUG: Token preview: {token[:50]}...")

#         if not token:
#             # Allow the endpoint to handle guest users
#             import inspect

#             sig = inspect.signature(f)
#             if "current_user" in sig.parameters:
#                 print("🔐 DEBUG: No token, calling function with None user")
#                 return f(None, *args, **kwargs)
#             else:
#                 return error_response("Token is missing!", 401)

#         try:
#             # Decode the token
#             print("🔐 DEBUG: Attempting to decode token")
#             data = jwt.decode(
#                 token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
#             )

#             print(f"🔐 DEBUG: Decoded token payload: {data}")

#             # Try different possible user ID fields
#             user_id = (
#                 data.get("id")  # Most common
#                 or data.get("user_id")  # Alternative
#                 or data.get(
#                     "sub"
#                 )  # JWT standard (this is what Flask-JWT-Extended uses)
#                 or data.get("user")  # Another alternative
#                 or data.get("uid")  # Another alternative
#             )

#             print(f"🔐 DEBUG: Extracted user_id: {user_id}")

#             if not user_id:
#                 print(
#                     f"❌ DEBUG: No user ID found in token payload. Available keys: {list(data.keys())}"
#                 )
#                 return error_response("Invalid token payload - no user identifier", 401)

#             # FIX: Use db directly instead of current_app.db
#             try:
#                 print(f"🔐 DEBUG: Querying database for user_id: {user_id}")
#                 result = db.session.execute(  # Use db directly here
#                     text(
#                         """
#                         SELECT id, username, email, role, firstname, lastname, avatar
#                         FROM users
#                         WHERE id = :user_id
#                     """
#                     ),
#                     {"user_id": user_id},
#                 )
#                 user_data = result.fetchone()

#                 if not user_data:
#                     print(f"❌ DEBUG: User not found in database for id: {user_id}")
#                     return error_response("User not found", 404)

#                 print(f"🔐 DEBUG: User found: {user_data[1]} (ID: {user_data[0]})")

#                 # Create a minimal user object with essential attributes
#                 class MinimalUser:
#                     def __init__(self, user_data):
#                         self.id = user_data[0]
#                         self.username = user_data[1]
#                         self.email = user_data[2]
#                         self.role = user_data[3]
#                         self.firstname = user_data[4]
#                         self.lastname = user_data[5]
#                         self.avatar = user_data[6]
#                         # Add empty relationships to avoid attribute errors
#                         self.joined_eras = []
#                         self.missions = []
#                         self.badges = []
#                         self.events = []
#                         self.rsvps = []
#                         self.poll_votes = []

#                 current_user = MinimalUser(user_data)
#                 print(f"🔐 DEBUG: Created MinimalUser with id: {current_user.id}")

#             except Exception as db_error:
#                 print(f"❌ DEBUG: Database error in token_required: {db_error}")
#                 import traceback

#                 print(f"❌ DEBUG: DB error traceback:\n{traceback.format_exc()}")
#                 return error_response("Database error during authentication", 500)

#         except jwt.ExpiredSignatureError:
#             print("❌ DEBUG: Token has expired")
#             return error_response("Token has expired!", 401)
#         except jwt.InvalidTokenError as e:
#             print(f"❌ DEBUG: JWT decode error: {e}")
#             return error_response("Invalid token!", 401)
#         except Exception as e:
#             print(f"❌ DEBUG: Unexpected error in token_required: {e}")
#             import traceback

#             print(f"❌ DEBUG: Unexpected error traceback:\n{traceback.format_exc()}")
#             return error_response("Authentication error", 401)

#         print(
#             f"🔐 DEBUG: Authentication successful, calling endpoint with user {current_user.id}"
#         )
#         return f(current_user, *args, **kwargs)

#     return decorated


def roles_required(*roles):
    """Restrict access to users with specific roles (e.g. admin, moderator)"""

    def wrapper(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if not current_user or current_user.role not in roles:
                return error_response("Permission denied", 403)
            return f(current_user, *args, **kwargs)

        return decorated

    return wrapper
