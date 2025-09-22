import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token
from app.extensions import db
from app.models import User
import os

# initialize firebase
# --- Firebase init (safe absolute path) ---
cred_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "firebase_service_key.json"
)
cred_path = os.path.abspath(cred_path)

if os.path.exists(cred_path) and not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
else:
    print(f"⚠️ Firebase credentials not found at {cred_path}. Skipping Firebase init.")
    
# cred = credentials.Certificate("firebase_service_key.json")
# firebase_admin.initialize_app(cred)

google_bp = Blueprint("google_auth", __name__, url_prefix="/auth/google")


@google_bp.route("/login", methods=["POST"])
def google_login():
    data = request.get_json()
    id_token = data.get("id_token")

    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        email = decoded_token.get("email")
        name = decoded_token.get("name", "User")

        user = User.query.filter_by(email=email).first()
        if not user:
            parts = name.split(" ", 1)
            firstname = parts[0]
            lastname = parts[1] if len(parts) > 1 else ""
            user = User(
                firstname=firstname,
                lastname=lastname,
                fullname=name,
                email=email,
                phone="",
                nationality="",
                referral=None,
                password_hash="",  # no password for google
                provider="google",
            )
            db.session.add(user)
            db.session.commit()

        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        return (
            jsonify({"access_token": access_token, "refresh_token": refresh_token}),
            200,
        )

    except Exception as e:
        return jsonify({"error": "Invalid Google token", "details": str(e)}), 401
