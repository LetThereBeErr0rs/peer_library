"""Authentication, authorization and CSRF behavior."""
from config import TestConfig
from app import create_app
from extensions import db as _db
from models import User


def test_register_creates_student(client):
    resp = client.post("/register", data={
        "display_name": "New Student", "email": "New@Example.com",
        "password": "password123", "confirm": "password123",
    }, follow_redirects=True)
    assert resp.status_code == 200
    user = User.query.filter_by(email="new@example.com").first()
    assert user is not None
    assert user.role == "student"           # never admin via public registration
    assert user.password_hash != "password123"  # hashed, not plaintext


def test_register_rejects_role_injection(client):
    client.post("/register", data={
        "display_name": "Sneaky", "email": "sneaky@example.com",
        "password": "password123", "confirm": "password123",
        "role": "admin",  # extra field must be ignored
    }, follow_redirects=True)
    user = User.query.filter_by(email="sneaky@example.com").first()
    assert user.role == "student"


def test_duplicate_email_rejected(client, make_user):
    make_user(email="dup@example.com")
    resp = client.post("/register", data={
        "display_name": "Dup", "email": "dup@example.com",
        "password": "password123", "confirm": "password123",
    })
    assert resp.status_code == 409


def test_login_wrong_password(client, make_user):
    make_user(email="a@example.com", password="rightpassword")
    resp = client.post("/login", data={"email": "a@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_logout_flow(client, make_user, login):
    make_user(email="a@example.com", password="password123")
    login("a@example.com", "password123")
    # Authenticated: contribute page is reachable.
    assert client.get("/contribute").status_code == 200
    client.post("/logout", follow_redirects=True)
    # After logout, contribute redirects to login.
    resp = client.get("/contribute")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_unauthenticated_upload_rejected(client):
    resp = client.post("/contribute", data={"title": "x", "description": "y",
                                             "resource_type": "notes"})
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_admin_only_moderation(client, make_user, login):
    from models import Resource
    r = Resource(title="T", description="D", resource_type="notes", status="published")
    _db.session.add(r)
    _db.session.commit()

    make_user(email="student@example.com", password="password123", role="student")
    login("student@example.com", "password123")
    resp = client.post(f"/admin/resource/{r.id}/status", data={"status": "hidden"})
    assert resp.status_code == 403  # students cannot moderate


def test_admin_can_moderate(client, make_user, login):
    from models import Resource
    r = Resource(title="T", description="D", resource_type="notes", status="published")
    _db.session.add(r)
    _db.session.commit()

    make_user(email="admin@example.com", password="password123", role="admin")
    login("admin@example.com", "password123")
    client.post(f"/admin/resource/{r.id}/status", data={"status": "hidden"},
                follow_redirects=True)
    assert _db.session.get(Resource, r.id).status == "hidden"


def test_csrf_blocks_unprotected_post(tmp_path):
    """With CSRF enabled, a POST without a token is rejected."""
    class _Config(TestConfig):
        WTF_CSRF_ENABLED = True
        UPLOAD_FOLDER = str(tmp_path / "uploads")

    app = create_app(_Config)
    with app.app_context():
        _db.create_all()
        client = app.test_client()
        resp = client.post("/register", data={
            "display_name": "X", "email": "x@example.com",
            "password": "password123", "confirm": "password123",
        })
        assert resp.status_code == 400  # CSRF token missing
        _db.drop_all()
