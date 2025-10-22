from flask import Blueprint
from flask import jsonify
from app import db

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return {"Paradox": "Hello Flask Backend!"}


@main.route("/health", methods=["GET"])
def health_check():
    try:
        db.session.execute(db.text("SELECT 1"))  # Quick DB ping
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


def init_routes(app):
    app.register_blueprint(main)
