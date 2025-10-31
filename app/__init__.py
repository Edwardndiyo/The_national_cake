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

    # with app.app_context():
    #     try:
    #         print("🔄 Running safe database schema check...")

    #         from sqlalchemy import inspect, text

    #         # Try normal migrations first
    #         try:
    #             from flask_migrate import upgrade

    #             upgrade()
    #             print("✅ Normal migrations applied successfully!")
    #             return  # Skip auto-migrate if normal migrations worked
    #         except Exception as migrate_error:
    #             print(f"⚠️  Normal migrations failed: {migrate_error}")
    #             print("🔄 Falling back to auto-column sync...")

    #         inspector = inspect(db.engine)

    #         # Get all tables from models
    #         tables = db.Model.__subclasses__()

    #         changes_made = False
    #         for table_class in tables:
    #             table_name = table_class.__tablename__

    #             try:
    #                 # Check if table exists
    #                 if not inspector.has_table(table_name):
    #                     print(f"⚠️  Table '{table_name}' doesn't exist - skipping")
    #                     continue

    #                 print(f"📋 Checking table: {table_name}")

    #                 # Get expected columns from model
    #                 expected_columns = {}
    #                 for column in table_class.__table__.columns:
    #                     expected_columns[column.name] = column.type

    #                 # Get existing columns from database
    #                 existing_columns = {
    #                     col["name"] for col in inspector.get_columns(table_name)
    #                 }

    #                 # Find and add ONLY missing columns (safe operation)
    #                 missing_columns = set(expected_columns.keys()) - existing_columns

    #                 for column_name in missing_columns:
    #                     column_type = expected_columns[column_name]
    #                     try:
    #                         # Convert SQLAlchemy type to SQL string
    #                         type_str = str(column_type).split("(")[
    #                             0
    #                         ]  # Simple type name

    #                         db.session.execute(
    #                             text(
    #                                 f"ALTER TABLE {table_name} ADD COLUMN {column_name} {type_str}"
    #                             )
    #                         )
    #                         print(
    #                             f"   ✅ Added column '{column_name}' ({type_str}) to '{table_name}'"
    #                         )
    #                         changes_made = True
    #                     except Exception as col_error:
    #                         print(
    #                             f"   ❌ Failed to add column '{column_name}': {col_error}"
    #                         )

    #             except Exception as table_error:
    #                 print(f"   ❌ Error processing table '{table_name}': {table_error}")

    #         if changes_made:
    #             db.session.commit()
    #             print("✅ Database schema sync completed with changes!")
    #         else:
    #             print("✅ Database schema is already in sync!")

    #     except Exception as e:
    #         print(f"❌ Database schema sync completely failed: {e}")
    #         db.session.rollback()

    with app.app_context():
        try:
            from sqlalchemy import text

            # Check and add missing columns to eras table
            result = db.session.execute(
                text(
                    """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='eras'
            """
                )
            )
            existing_columns = {row[0] for row in result}

            missing_columns = []
            if "year_range" not in existing_columns:
                missing_columns.append("ADD COLUMN year_range VARCHAR(50)")
            if "image" not in existing_columns:
                missing_columns.append("ADD COLUMN image VARCHAR(255)")

            if missing_columns:
                print("🔄 Adding missing columns to eras table...")
                alter_sql = f"ALTER TABLE eras {', '.join(missing_columns)}"
                db.session.execute(text(alter_sql))
                db.session.commit()
                print("✅ Added missing columns to eras table!")

        except Exception as e:
            print(f"❌ Could not auto-add columns: {e}")
            db.session.rollback()

    with app.app_context():
        try:
            from flask_migrate import upgrade

            print("🔄 Applying migrations on startup...")
            upgrade()
            print("✅ Migrations applied successfully!")
        except Exception as e:
            print(f"❌ Migration failed: {e}")

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
