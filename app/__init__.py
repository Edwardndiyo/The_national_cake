from flask import Flask
# import ssl, certifi
from flask_cors import CORS

# ssl._create_default_https_context = lambda: ssl.create_default_context(
#     cafile=certifi.where()
# )

# from flask_sqlalchemy import SQLAlchemy
# from flask_migrate import Migrate
# from flask_jwt_extended import JWTManager
# from flask_socketio import SocketIO
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


# db = SQLAlchemy()
# migrate = Migrate()
# jwt = JWTManager()
# socketio = SocketIO(cors_allowed_origins="*")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ✅ Enable CORS
    # CORS(app, resources={r"/*": {"origins": "*"}})
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
        "version": "1.0.0"
    },
    "basePath": "/",
    "schemes": [
        "http",
        "https"
    ]
}

    swagger = Swagger(app, template=swagger_template)

    # swagger = Swagger(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        db.create_all()  # Fallback for initial table creation
    jwt.init_app(app)
    socketio.init_app(app)
    mail.init_app(app)

    # --- AUTO MIGRATE ON FIRST REQUEST ---
    @app.before_request
    def auto_migrate():
        if not hasattr(auto_migrate, "ran"):
            with app.app_context():
                from flask_migrate import upgrade

                upgrade()  # Runs `alembic upgrade head`
                print("Migrations applied!")
            auto_migrate.ran = True

    # --- CLI COMMAND (optional) ---
    @app.cli.command("db-migrate")
    def db_migrate():
        """Run migrations manually"""
        with app.app_context():
            from flask_migrate import upgrade

            upgrade()
            print("Migrations applied via CLI!")
            

    # Import models for migration detection

    # Register routes
    from app.routes import init_routes
    # from routes.auth import auth_bp
    # from routes.auth import google_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(google_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(badge_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(feedback_bp)

    init_routes(app)

    # Middlewares
    from app.middlewares import register_middlewares

    register_middlewares(app)

    return app


# Connectivity & security
# Endpoint & port
# Endpoint
# nationalcake-aurora.cp0caiqkk957.eu-west-1.rds.amazonaws.com
# Port
# 5432
# Networking
# Availability Zone
# eu-west-1c
# VPC
# vpc-06f451f3ddc9c72f9
# Subnet group
# rds-ec2-db-subnet-group-1
# Subnets
# subnet-040ca364ae24f73f2
# subnet-024b947f079083f0c
# subnet-0a9afe6fa35ef9fa6
# Network type
# IPv4
# Security
# VPC security groups
# rds-ec2-3 (sg-05d9437e496c2256e)
# Active
# Publicly accessible
# No
# Certificate authority
# Info
# rds-ca-rsa2048-g1


# EB - Elastic Beanstalk

# nstances
# IMDSv1
# Disabled
# EC2 Security Groups
# awseb-e-wpt8vtawft-stack-AWSEBSecurityGroup-lJTjmjG4zsYd
# Capacity
# Environment type
# Load balanced
# Min instances
# 1
# Max instances
# 4
# Fleet composition
# On-Demand instances
# On-demand base
# 0
# On-demand above base
# 70
# Capacity rebalancing
# Disabled
# Scaling cooldown
# 360
# Processor type
# x86_64
# Instance types
# t3.micro, t3.small
# AMI ID
# ami-0bb15d1fcb59d4d07
