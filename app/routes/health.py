# In app/routes/__init__.py or create app/routes/health.py
from flask import Blueprint, jsonify
from app.extensions import db
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check and database initialization endpoint"""
    try:
        # Try to create tables if they don't exist
        db.create_all()
        
        # Test database connection
        db.session.execute('SELECT 1')
        
        return jsonify({
            "status": "healthy",
            "service": "National Cake Community API", 
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Database tables initialized successfully"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "service": "National Cake Community API",
            "database": "disconnected", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500