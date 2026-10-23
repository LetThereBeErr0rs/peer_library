"""Peer Library application factory.

``app = create_app()`` at module level keeps the Gunicorn entrypoint ``app:app``
working. The factory wires up configuration, extensions, blueprints, error
handling and CLI commands.

Schema is managed by Flask-Migrate (``flask db upgrade``), NOT by
``db.create_all()`` at startup, so Gunicorn workers never race to build tables.
"""
import logging
import os

import click
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from config import select_config, is_production
from extensions import db, migrate, login_manager, csrf, limiter
from security import linkify, apply_security_headers

load_dotenv()

logging.basicConfig(level=logging.INFO)


def create_app(config_class=None):
    app = Flask(__name__)
    app.config.from_object(config_class or select_config())

    # Fail fast on a misconfigured production deployment.
    if is_production(app):
        from config import Config

        Config.validate_production(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # --- extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    if app.config.get("RATELIMIT_ENABLED", True):
        limiter.init_app(app)

    # Import models so they are registered with SQLAlchemy / Alembic.
    from models import User  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- blueprints ---
    from views import main_bp
    from auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    # --- jinja helpers ---
    app.jinja_env.filters["linkify"] = linkify

    @app.context_processor
    def inject_globals():
        from forms import LoginForm  # lightweight; used for navbar state

        return {"ALLOWED_MAX_MIB": app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)}

    # --- security headers ---
    app.after_request(apply_security_headers)

    _register_error_handlers(app)
    _register_cli(app)

    return app


def _wants_json():
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def _register_error_handlers(app):
    def handle(code, message):
        if _wants_json():
            return jsonify({"error": message}), code
        try:
            return render_template("error.html", code=code, message=message), code
        except Exception:
            return message, code

    @app.errorhandler(400)
    def bad_request(e):
        return handle(400, "Bad request.")

    @app.errorhandler(403)
    def forbidden(e):
        return handle(403, "You do not have permission to do that.")

    @app.errorhandler(404)
    def not_found(e):
        return handle(404, "That page or resource could not be found.")

    @app.errorhandler(410)
    def gone(e):
        return handle(410, "This file is no longer available.")

    @app.errorhandler(413)
    def too_large(e):
        return handle(413, "The upload is larger than the allowed limit.")

    @app.errorhandler(429)
    def rate_limited(e):
        return handle(429, "Too many requests. Please slow down and try again.")

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error")
        return handle(500, "An unexpected error occurred.")

    @app.errorhandler(HTTPException)
    def http_exception(e):
        # Fallback for any other HTTP error; preserves its code.
        return handle(e.code or 500, e.description or "Error")


def _register_cli(app):
    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("display_name")
    @click.password_option()
    def create_admin(email, display_name, password):
        """Create (or promote) an administrator account."""
        from models import User

        email = User.normalize_email(email)
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email, display_name=display_name, role="admin")
            user.set_password(password)
            db.session.add(user)
            click.echo(f"Created admin {email}.")
        else:
            user.role = "admin"
            user.set_password(password)
            click.echo(f"Promoted existing user {email} to admin.")
        db.session.commit()


# Gunicorn entrypoint: ``gunicorn app:app``.
app = create_app()


if __name__ == "__main__":
    # Local development server only. Production uses Gunicorn.
    app.run(host="0.0.0.0", port=5000, debug=app.config.get("ENV") != "production")
