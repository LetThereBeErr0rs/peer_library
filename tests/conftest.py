"""Shared pytest fixtures.

Tests run against an in-memory SQLite database and a temporary local upload
folder — no real credentials or external services are touched.
"""
import io
import os
import zipfile

import pytest

os.environ["FLASK_ENV"] = "testing"

from app import create_app  # noqa: E402
from config import TestConfig  # noqa: E402
from extensions import db as _db  # noqa: E402
from models import User  # noqa: E402


@pytest.fixture
def app(tmp_path):
    class _Config(TestConfig):
        UPLOAD_FOLDER = str(tmp_path / "uploads")

    application = create_app(_Config)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def make_user(app):
    def _make(email="student@example.com", password="password123", role="student",
              display_name="Test Student", roll_number="R-1"):
        user = User(email=User.normalize_email(email), display_name=display_name,
                    role=role, roll_number=roll_number)
        user.set_password(password)
        _db.session.add(user)
        _db.session.commit()
        return user
    return _make


@pytest.fixture
def login(client):
    def _login(email="student@example.com", password="password123"):
        return client.post("/login", data={"email": email, "password": password},
                           follow_redirects=True)
    return _login


# --- file-builder helpers ---
def make_pdf(size=1024):
    return b"%PDF-1.4\n" + b"0" * max(0, size - 9)


def make_png():
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def make_jpeg():
    return b"\xff\xd8\xff\xe0" + b"\x00" * 64


def make_txt():
    return b"These are plain study notes.\n"


def make_docx():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("word/document.xml", "<document/>")
    return buf.getvalue()


def upload_tuple(data, filename):
    return (io.BytesIO(data), filename)
