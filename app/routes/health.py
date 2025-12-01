from flask import Blueprint, jsonify
from app.extensions import db
from datetime import datetime
from sqlalchemy import text  # <-- Add this import

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Health check and database initialization endpoint"""
    try:
        # Try to create tables if they don't exist
        db.create_all()

        # Test database connection - FIXED: use text()
        db.session.execute(text("SELECT 1"))

        return (
            jsonify(
                {
                    "status": "healthy",
                    "service": "National Cake Community API",
                    "database": "connected",
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": "Database tables initialized successfully",
                }
            ),
            200,
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "service": "National Cake Community API",
                    "database": "disconnected",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            500,
        )
