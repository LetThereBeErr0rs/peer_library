"""Environment-based application configuration.

The database URL and storage backend are chosen from environment variables so
that the same code runs against local SQLite in development and Supabase
PostgreSQL in production. Nothing secret is hard-coded here.
"""
import os


# 25 MiB hard upload limit, shared by Flask (MAX_CONTENT_LENGTH) and our own
# validation so the two layers always agree.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

# Allowlist of extensions appropriate for academic files.
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt", "docx"}


def _normalize_db_url(url):
    """Make a database URL usable by SQLAlchemy.

    Supabase/Heroku-style URLs often start with ``postgres://``; SQLAlchemy
    wants ``postgresql+psycopg://`` so the modern psycopg (v3) driver is used.
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration shared by every environment."""

    # --- Core ---
    ENV = os.environ.get("FLASK_ENV", "development")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")

    # --- Database ---
    # Default to a local SQLite file inside instance/. This is a *new* database,
    # separate from the legacy instance/database.db which is preserved as the
    # migration source.
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.environ.get("DATABASE_URL")) or (
        "sqlite:///peer_library.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # --- Uploads / storage ---
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")  # local | supabase
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")

    # Supabase (server-side only – never expose the service key to the browser)
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
    SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "resources")
    SUPABASE_SIGNED_URL_TTL = int(os.environ.get("SUPABASE_SIGNED_URL_TTL", "120"))

    # --- Sessions / cookies ---
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), default=False)
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("SESSION_LIFETIME", "86400"))

    # --- CORS (Explicit allowlist for decoupled frontends on Vercel) ---
    CORS_ALLOWED_ORIGINS = [
        o.strip()
        for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]

    # --- CSRF (Flask-WTF) ---
    WTF_CSRF_ENABLED = True

    # --- Rate limiting ---
    RATELIMIT_ENABLED = _bool(os.environ.get("RATELIMIT_ENABLED"), default=True)
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # Pagination
    RESOURCES_PER_PAGE = int(os.environ.get("RESOURCES_PER_PAGE", "12"))

    @staticmethod
    def validate_production(app):
        """Fail loudly if production is misconfigured.

        Called at startup. In production we refuse to run with an insecure
        secret key, and we require real database + storage configuration rather
        than silently falling back to ephemeral local storage.
        """
        problems = []
        if app.config["SECRET_KEY"] in (None, "", "dev-insecure-change-me"):
            problems.append("SECRET_KEY must be set to a strong random value.")
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            problems.append(
                "DATABASE_URL must point at PostgreSQL in production, not SQLite."
            )
        if app.config["STORAGE_BACKEND"] != "supabase":
            problems.append(
                "STORAGE_BACKEND must be 'supabase' in production "
                "(local filesystem storage is ephemeral in containers)."
            )
        else:
            for key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_BUCKET"):
                if not app.config.get(key):
                    problems.append(f"{key} is required when STORAGE_BACKEND=supabase.")
        if problems:
            raise RuntimeError(
                "Invalid production configuration:\n  - " + "\n  - ".join(problems)
            )


class TestConfig(Config):
    """Isolated configuration for the automated test suite."""

    TESTING = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    STORAGE_BACKEND = "local"
    WTF_CSRF_ENABLED = False  # forms are exercised directly; CSRF has its own tests
    RATELIMIT_ENABLED = False


def select_config():
    """Return the config class for the current environment."""
    if os.environ.get("FLASK_ENV") == "testing":
        return TestConfig
    return Config


def is_production(app):
    return app.config.get("ENV") == "production"
