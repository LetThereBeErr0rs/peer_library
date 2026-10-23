"""WTForms definitions.

Flask-WTF gives us CSRF protection and server-side validation for free. The
same rules are enforced here regardless of what the browser did.
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    PasswordField,
    TextAreaField,
    SelectField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    Optional,
)

from config import ALLOWED_EXTENSIONS
from models import Resource


class RegisterForm(FlaskForm):
    display_name = StringField("Display name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=8, max=128)]
    )
    confirm = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    roll_number = StringField("Roll number (optional)", validators=[Optional(), Length(max=50)])
    department = StringField("Department (optional)", validators=[Optional(), Length(max=120)])


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired()])


class UploadForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200)])
    resource_type = SelectField(
        "Resource type",
        choices=[(t, t.title()) for t in Resource.RESOURCE_TYPES],
        validators=[DataRequired()],
    )
    subject = StringField("Subject", validators=[Optional(), Length(max=120)])
    category = StringField("Category", validators=[Optional(), Length(max=120)])
    semester = StringField("Semester", validators=[Optional(), Length(max=40)])
    department = StringField("Department", validators=[Optional(), Length(max=120)])
    description = TextAreaField(
        "Description / learning content", validators=[DataRequired(), Length(max=20000)]
    )
    # Client-side convenience only; the real check is in validation.py.
    file = FileField(
        "Attachment (optional)",
        validators=[Optional(), FileAllowed(ALLOWED_EXTENSIONS, "Unsupported file type.")],
    )
