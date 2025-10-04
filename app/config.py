import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///ncc_dev.db"  # fallback
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail config
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

    DEBUG = True
