"""Authentication blueprint: register, login, logout.

Uses Flask-Login for sessions and Werkzeug's password hashing (scrypt by
default) – no custom cryptography. Registration can never assign the admin
role; that is set out-of-band (see the ``create-admin`` CLI command).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
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
