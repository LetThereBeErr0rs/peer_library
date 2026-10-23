"""Authentication blueprint: register, login, logout.

Uses Flask-Login for sessions and Werkzeug's password hashing (scrypt by
default) – no custom cryptography. Registration can never assign the admin
role; that is set out-of-band (see the ``create-admin`` CLI command).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError

from extensions import db, limiter
from models import User
from forms import RegisterForm, LoginForm
from security import is_safe_redirect_target

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = User.normalize_email(form.email.data)
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("register.html", form=form), 409

        user = User(
            email=email,
            display_name=form.display_name.data.strip(),
            roll_number=(form.roll_number.data or "").strip() or None,
            department=(form.department.data or "").strip() or None,
            role="student",  # public registration is always a student
        )
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An account with that email already exists.", "danger")
            return render_template("register.html", form=form), 409

        login_user(user)
        flash("Welcome to Peer Library!", "success")
        return redirect(url_for("main.index"))

    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = User.normalize_email(form.email.data)
        user = User.query.filter_by(email=email).first()
        # Same generic message whether the email or password was wrong.
        if user is None or not user.check_password(form.password.data):
            flash("Incorrect email or password.", "danger")
            return render_template("login.html", form=form), 401
        if not user.is_active:
            flash("This account is disabled.", "danger")
            return render_template("login.html", form=form), 403

        login_user(user)
        nxt = request.args.get("next")
        if nxt and is_safe_redirect_target(nxt):
            return redirect(nxt)
        return redirect(url_for("main.index"))

    return render_template("login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


# --- API endpoints for decoupled / static frontends (Vercel) ---

@auth_bp.route("/api/auth/csrf", methods=["GET"])
def api_csrf():
    """Return a fresh CSRF token associated with the session cookie."""
    return jsonify({"csrf_token": generate_csrf()})


@auth_bp.route("/api/auth/me", methods=["GET"])
def api_me():
    """Return current session state for the client-side navbar/auth state."""
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False, "user": None})
    return jsonify(
        {
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "display_name": current_user.display_name,
                "roll_number": current_user.roll_number,
                "department": current_user.department,
                "role": current_user.role,
                "is_admin": current_user.is_admin,
            },
        }
    )


@auth_bp.route("/api/auth/login", methods=["POST"])
@limiter.limit("20 per hour", methods=["POST"])
def api_login():
    """JSON/form login endpoint for decoupled frontends."""
    data = request.get_json(silent=True) or request.form
    email = User.normalize_email(data.get("email"))
    password = data.get("password") or ""

    if not email and not password and current_user.is_authenticated:
        return jsonify(
            {
                "success": True,
                "user": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "display_name": current_user.display_name,
                    "role": current_user.role,
                    "is_admin": current_user.is_admin,
                },
            }
        )

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({"error": "Incorrect email or password."}), 401
    if not user.is_active:
        return jsonify({"error": "This account is disabled."}), 403

    login_user(user)
    return jsonify(
        {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "role": user.role,
                "is_admin": user.is_admin,
            },
        }
    )


@auth_bp.route("/api/auth/register", methods=["POST"])
@limiter.limit("10 per hour", methods=["POST"])
def api_register():
    """JSON/form registration endpoint for decoupled frontends."""
    data = request.get_json(silent=True) or request.form
    email = User.normalize_email(data.get("email"))
    display_name = (data.get("display_name") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirm") or ""
    roll_number = (data.get("roll_number") or "").strip() or None
    department = (data.get("department") or "").strip() or None

    if not display_name:
        return jsonify({"error": "Display name is required."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "A valid email address is required."}), 400
    if not password or len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long."}), 400
    if confirm and password != confirm:
        return jsonify({"error": "Passwords do not match."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with that email already exists."}), 409

    user = User(
        email=email,
        display_name=display_name,
        roll_number=roll_number,
        department=department,
        role="student",
    )
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "An account with that email already exists."}), 409

    login_user(user)
    return (
        jsonify(
            {
                "success": True,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "role": user.role,
                    "is_admin": user.is_admin,
                },
            }
        ),
        201,
    )


@auth_bp.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    """JSON logout endpoint."""
    logout_user()
    return jsonify({"success": True, "message": "You have been logged out."})

