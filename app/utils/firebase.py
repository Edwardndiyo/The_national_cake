import firebase_admin
from firebase_admin import credentials, auth

FIREBASE_KEY_PATH = "firebase_service_key.json"


# Only initialize when needed
def get_firebase_app():
    if not firebase_admin._apps:
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)
    return firebase_admin.get_app()


def verify_firebase_token(token):
    try:
        get_firebase_app()
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        return None
    


# import os
# import firebase_admin
# from firebase_admin import credentials, auth

# FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "firebase_service_key.json")

# firebase_app = None

# if os.path.exists(FIREBASE_KEY_PATH):
#     cred = credentials.Certificate(FIREBASE_KEY_PATH)
#     firebase_app = firebase_admin.initialize_app(cred)
# else:
#     print("⚠️ Firebase service key not found, skipping Firebase init")

# def verify_firebase_token(id_token):
#     if not firebase_app:
#         return None
#     try:
#         decoded = auth.verify_id_token(id_token, app=firebase_app)
#         return decoded
#     except Exception:
#         return None


# import firebase_admin
# from firebase_admin import auth as firebase_auth, credentials
# import os

# FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "firebase_service_key.json")

# if not firebase_admin._apps:
#     cred = credentials.Certificate(FIREBASE_KEY_PATH)
#     firebase_admin.initialize_app(cred)


# def verify_firebase_token(id_token: str):
#     """
#     Verify a Firebase ID token sent by the client.
#     Returns decoded user info if valid, otherwise None.
#     """
#     try:
#         decoded_token = firebase_auth.verify_id_token(id_token)
#         return decoded_token
#     except Exception:
#         return None
