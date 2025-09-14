import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

    # Try PostgreSQL, fallback to SQLite
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///ncc_dev.db"  # fallback
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = True
