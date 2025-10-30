# from flask import Flask
# # import ssl, certifi
# from flask_cors import CORS

# # ssl._create_default_https_context = lambda: ssl.create_default_context(
# #     cafile=certifi.where()
# # )

# # from flask_sqlalchemy import SQLAlchemy
# # from flask_migrate import Migrate
# # from flask_jwt_extended import JWTManager
# # from flask_socketio import SocketIO
# from app.config import Config
# from app.extensions import db, migrate, jwt, mail, socketio
# from app.models import *  # import all models so Alembic sees them
# from app.routes.auth.auth import auth_bp
# from app.routes.auth.google import google_bp
# from app.middlewares import register_middlewares
# from app.routes.profile.routes import profile_bp
# from app.routes.community.routes import community_bp
# from app.routes.badges.routes import badge_bp
# from app.routes.events.routes import events_bp
# from app.routes.feedback.routes import feedback_bp
# from flasgger import Swagger


# # db = SQLAlchemy()
# # migrate = Migrate()
# # jwt = JWTManager()
# # socketio = SocketIO(cors_allowed_origins="*")


# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     # ✅ Enable CORS
#     # CORS(app, resources={r"/*": {"origins": "*"}})
#     CORS(
#         app,
#         resources={r"/*": {"origins": "*"}},
#         supports_credentials=True,
#         allow_headers="*",
#     )

#     swagger_template = {
#     "swagger": "2.0",
#     "info": {
#         "title": "The National Cake API",
#         "description": "API documentation for The National Cake backend built with Flask By Paradox",
#         "version": "1.0.0"
#     },
#     "basePath": "/",
#     "schemes": [
#         "http",
#         "https"
#     ]
# }

#     swagger = Swagger(app, template=swagger_template)

#     # swagger = Swagger(app)

#     # Initialize extensions
#     db.init_app(app)
#     migrate.init_app(app, db)
#     # with app.app_context():
#     #     db.create_all()  # Fallback for initial table creation
#     jwt.init_app(app)
#     socketio.init_app(app)
#     mail.init_app(app)

#     # --- AUTO MIGRATE ON FIRST REQUEST ---
#     @app.before_request
#     def auto_migrate():
#         if not hasattr(auto_migrate, "ran"):
#             with app.app_context():
#                 from flask_migrate import upgrade

#                 upgrade()  # Runs `alembic upgrade head`
#                 print("Migrations applied!")
#             auto_migrate.ran = True

#     # --- CLI COMMAND (optional) ---
#     @app.cli.command("db-migrate")
#     def db_migrate():
#         """Run migrations manually"""
#         with app.app_context():
#             from flask_migrate import upgrade

#             upgrade()
#             print("Migrations applied via CLI!")


#     # Import models for migration detection

#     # Register routes
#     from app.routes import init_routes
#     # from routes.auth import auth_bp
#     # from routes.auth import google_bp

#     app.register_blueprint(auth_bp)
#     app.register_blueprint(google_bp)
#     app.register_blueprint(profile_bp)
#     app.register_blueprint(community_bp)
#     app.register_blueprint(badge_bp)
#     app.register_blueprint(events_bp)
#     app.register_blueprint(feedback_bp)

#     init_routes(app)

#     # Middlewares
#     from app.middlewares import register_middlewares

#     register_middlewares(app)

#     return app


from flask import Flask
import os
from flask_cors import CORS
from app.config import Config
from app.extensions import db, migrate, jwt, mail, socketio
from app.models import *  # import all models so Alembic sees them
from app.routes.auth.auth import auth_bp
from app.routes.auth.google import google_bp
from app.middlewares import register_middlewares
from app.routes.profile.routes import profile_bp
from app.routes.community.routes import community_bp
from app.routes.badges.routes import badge_bp
from app.routes.events.routes import events_bp
from app.routes.feedback.routes import feedback_bp
from flasgger import Swagger


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

    # ✅ Run migrations ONLY ONCE when app starts

    with app.app_context():
        try:
            # Check if year_range column exists
            from sqlalchemy import text

            result = db.session.execute(
                text(
                    """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='eras' AND column_name='year_range'
            """
                )
            )
            if not result.fetchone():
                print("🔄 Adding missing 'year_range' column to eras table...")
                db.session.execute(
                    text("ALTER TABLE eras ADD COLUMN year_range VARCHAR(50)")
                )
                db.session.commit()
                print("✅ Added missing column!")
        except Exception as e:
            print(f"❌ Could not auto-add column: {e}")
    # with app.app_context():
    #     try:
    #         from flask_migrate import upgrade

    #         print("🔄 Applying migrations on startup...")
    #         upgrade()
    #         print("✅ Migrations applied successfully!")
    #     except Exception as e:
    #         print(f"❌ Migration failed: {e}")

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

    from app.routes import init_routes

    init_routes(app)

    # Middlewares
    register_middlewares(app)

    return app
