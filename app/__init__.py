from flask import Flask
import os
from flask_cors import CORS
from app.config import Config
from app.extensions import db, migrate, jwt, mail, socketio
# from app.models import *  # import all models so Alembic sees them
# In app/__init__.py, before the models import
print("🔍 DEBUG: Starting model imports...")
try:
    from app.models import *

    print("✅ DEBUG: All models imported successfully")
except Exception as e:
    print(f"❌ DEBUG: Error importing models: {e}")
    import traceback

    print(f"❌ DEBUG: Import traceback:\n{traceback.format_exc()}")
from app.routes.auth.auth import auth_bp
from app.routes.auth.google import google_bp
from app.middlewares import register_middlewares
from app.routes.profile.routes import profile_bp
from app.routes.community.routes import community_bp
from app.routes.badges.routes import badge_bp
from app.routes.events.routes import events_bp
from app.routes.feedback.routes import feedback_bp
from flasgger import Swagger
from app.routes.health import health_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers="*",
    )

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "The National Cake API",
            "description": "API documentation for The National Cake backend built with Flask By Paradox",
            "version": "1.0.0",
        },
        "basePath": "/",
        "schemes": ["http", "https"],
    }

    swagger = Swagger(app, template=swagger_template)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    socketio.init_app(app)
    mail.init_app(app)

    # --- ADD THIS: Automatic database initialization ---
    with app.app_context():
        try:
            print("🔄 Checking database tables...")
            # Try to create all tables
            db.create_all()
            print("✅ Database tables created/verified successfully!")
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            import traceback

            print(f"❌ TRACEBACK:\n{traceback.format_exc()}")

    # --- SIMPLE MIGRATION COMMAND ---
    @app.cli.command("db-migrate")
    def db_migrate():
        """Run migrations manually"""
        with app.app_context():
            from flask_migrate import upgrade

            upgrade()
            print("Migrations applied via CLI!")

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(google_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(badge_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(feedback_bp)
    app.register_blueprint(health_bp)

    from app.routes import init_routes

    init_routes(app)

    # Middlewares
    register_middlewares(app)

    return app
