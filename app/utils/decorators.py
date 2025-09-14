# app/utils/decorators.py
from flask_jwt_extended import get_jwt_identity
from functools import wraps
from app.models import User
from app import db
from app.utils.responses import error_response


def role_required(roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            user_id = get_jwt_identity()
            if not user_id:
                return error_response("Unauthorized", 401)
            user = db.session.get(User, user_id)
            if not user or user.role not in roles:
                return error_response("Forbidden: insufficient role", 403)
            return fn(*args, **kwargs)

        return decorator

    return wrapper
