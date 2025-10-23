import os
from pathlib import Path


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

    # === DATABASE CONFIG ===
    @staticmethod
    def get_database_uri():
        """
        Determine which database to use:
        - Prefer DATABASE_URL (for Elastic Beanstalk / Aurora)
        - Else, build from DB_* env vars
        - Else, fallback to local SQLite
        """
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url

        # Build from individual env vars (optional)
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASS")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME")

        if all([db_user, db_pass, db_host, db_name]):
            return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

        # Fallback to SQLite locally
        base_dir = Path(__file__).resolve().parent
        sqlite_path = base_dir / "ncc_dev.db"
        return f"sqlite:///{sqlite_path}"

    SQLALCHEMY_DATABASE_URI = get_database_uri.__func__()  # call static method
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # === MAIL CONFIG ===
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "False").lower() in ("true", "1", "t")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1", "t")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv(
        "MAIL_DEFAULT_SENDER", "noreply@thenationalcake.com"
    )

    MAIL_BACKEND = os.getenv("MAIL_BACKEND", "smtp")

    DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")


# import os


# class Config:
#     SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

#     # Database
#     SQLALCHEMY_DATABASE_URI = os.getenv(
#         # "DATABASE_URL", "sqlite:////tmp/ncc_dev.db"
#         "DATABASE_URL",
#         "sqlite:///ncc_dev.db",  # fallback
#         # # fallback
#     )
#     SQLALCHEMY_TRACK_MODIFICATIONS = False

#     # Mail config
#     MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
#     MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
#     MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "False").lower() in ("true", "1", "t")
#     MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1", "t")
#     MAIL_USERNAME = os.getenv("MAIL_USERNAME")
#     MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
#     MAIL_DEFAULT_SENDER = os.getenv(
#         "MAIL_DEFAULT_SENDER", "noreply@thenationalcake.com"
#     )

#     MAIL_BACKEND = os.getenv("MAIL_BACKEND", "smtp")

#     DEBUG = True
