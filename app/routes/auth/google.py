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
    """
    openapi: 3.0.0
info:
  title: Google Authentication API
  description: API for logging in users using Google Sign-In (Firebase).
  version: 1.0.0

servers:
  - url: http://localhost:5000
    description: Local development server
  - url: https://your-deployed-domain.com
    description: Production server

paths:
  /auth/google/login:
    post:
      summary: Login with Google
      description: >
        Authenticate a user using their Google ID token.  
        The token is verified with Firebase.  
        If the user does not exist in the database, a new one will be created.  
        Returns access and refresh JWT tokens.
      tags:
        - Authentication
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - id_token
              properties:
                id_token:
                  type: string
                  description: Google ID token obtained from the frontend after Google Sign-In.
                  example: eyJhbGciOiJSUzI1NiIsImtpZCI6IjA1...
      responses:
        "200":
          description: Successful login
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                    description: JWT access token
                    example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
                  refresh_token:
                    type: string
                    description: JWT refresh token
                    example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        "401":
          description: Invalid or expired Google token
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    example: Invalid Google token
                  details:
                    type: string
                    example: Token signature expired or invalid
        "500":
          description: Internal server error
    """
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
