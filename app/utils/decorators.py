# app/utils/decorators.py
from functools import wraps
from flask import request
import jwt
from app.models import User
from app.utils.responses import error_response
from flask import current_app


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]  # "Bearer <token>"

        if not token:
            return error_response("Token is missing!", 401)

        try:
            data = jwt.decode(
                token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
            )
            current_user = User.query.get(data["id"])
            if not current_user:
                return error_response("User not found", 404)
        except jwt.ExpiredSignatureError:
            return error_response("Token has expired!", 401)
        except jwt.InvalidTokenError:
            return error_response("Invalid token!", 401)

        return f(current_user, *args, **kwargs)

    return decorated


def roles_required(*roles):
    """Restrict access to users with specific roles (e.g. admin, moderator)"""

    def wrapper(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.role not in roles:
                return error_response("Permission denied", 403)
            return f(current_user, *args, **kwargs)

        return decorated

    return wrapper

