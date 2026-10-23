"""Shared Flask extension instances.

Kept in their own module so models, the app factory and the CLI can all import
the same objects without creating circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

# Where anonymous users are sent when they hit a protected page.
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"
