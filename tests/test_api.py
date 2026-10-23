"""Tests for REST API endpoints serving the decoupled static frontend."""
import io
from extensions import db as _db
from models import User, Resource, ResourceFile


def test_health_endpoints(client):
    res1 = client.get("/healthz")
    assert res1.status_code == 200
    assert res1.get_json()["status"] == "ok"

    res2 = client.get("/api/health")
    assert res2.status_code == 200
    assert res2.get_json()["status"] == "ok"


def test_api_csrf_endpoint(client):
    res = client.get("/api/auth/csrf")
    assert res.status_code == 200
    data = res.get_json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 0


def test_api_auth_me_unauthenticated(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is False
    assert data["user"] is None


def test_api_register_and_login_flow(client):
    # Register
    reg_res = client.post(
        "/api/auth/register",
        json={
            "display_name": "API Tester",
            "email": "apitester@college.edu",
            "password": "Password123!",
            "confirm": "Password123!",
            "roll_number": "2024CS099",
            "department": "CSE",
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.get_json()
    assert reg_data["success"] is True
    assert reg_data["user"]["email"] == "apitester@college.edu"
    assert reg_data["user"]["role"] == "student"

    # Verify session is active
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.get_json()["authenticated"] is True
    assert me_res.get_json()["user"]["display_name"] == "API Tester"

    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.get_json()["success"] is True

    # After logout, me is unauthenticated
    assert client.get("/api/auth/me").get_json()["authenticated"] is False

    # Login with valid credentials
    login_res = client.post(
        "/api/auth/login",
        json={"email": "apitester@college.edu", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    assert login_res.get_json()["success"] is True

    # Bad password
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "apitester@college.edu", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401
    assert "error" in bad_login.get_json()


def test_api_register_duplicate_email(client):
    payload = {
        "display_name": "User One",
        "email": "dupe@college.edu",
        "password": "Password123!",
    }
    r1 = client.post("/api/auth/register", json=payload)
    assert r1.status_code == 201

    # Attempt duplicate
    r2 = client.post("/api/auth/register", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.get_json()["error"]


def test_api_register_validation(client):
    # Short password
    r1 = client.post(
        "/api/auth/register",
        json={"display_name": "Test", "email": "short@college.edu", "password": "123"},
    )
    assert r1.status_code == 400

    # Missing email
    r2 = client.post(
        "/api/auth/register",
        json={"display_name": "Test", "password": "Password123!"},
    )
    assert r2.status_code == 400


def test_api_resource_detail(client):
    resource = Resource(
        title="Discrete Mathematics Notes",
        description="Graph theory summaries",
        resource_type="notes",
        subject="Mathematics",
        status="published",
    )
    _db.session.add(resource)
    _db.session.commit()

    res = client.get(f"/api/resources/{resource.id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "Discrete Mathematics Notes"
    assert data["subject"] == "Mathematics"
    assert data["description"] == "Graph theory summaries"

    # Nonexistent
    assert client.get("/api/resources/99999").status_code == 404


def test_api_resource_detail_hidden_permissions(client, make_user, login):
    user = make_user(email="hidden_owner@college.edu", password="password123")
    hidden = Resource(
        title="Draft Exam Paper",
        description="Confidential until exam date",
        resource_type="paper",
        status="hidden",
        uploader_id=user.id,
    )
    _db.session.add(hidden)
    _db.session.commit()

    # Unauthenticated visitor gets 404 (does not disclose existence)
    assert client.get(f"/api/resources/{hidden.id}").status_code == 404

    # Owner can view after login
    login("hidden_owner@college.edu", "password123")
    assert client.get(f"/api/resources/{hidden.id}").status_code == 200


def test_api_create_resource(client, make_user, login):
    user = make_user(email="creator@college.edu", password="password123")
    login("creator@college.edu", "password123")

    # Text-only resource
    res = client.post(
        "/api/resources",
        data={
            "title": "Algorithms Cheat Sheet",
            "description": "Big-O complexities and sorting algorithms",
            "resource_type": "notes",
            "subject": "CS",
            "category": "Cheatsheet",
        },
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["resource"]["title"] == "Algorithms Cheat Sheet"

    # Resource with permitted file upload
    fake_pdf = io.BytesIO(b"%PDF-1.4 header and content")
    res_file = client.post(
        "/api/resources",
        data={
            "title": "Operating Systems Syllabus",
            "description": "Weekly course schedule",
            "resource_type": "syllabus",
            "file": (fake_pdf, "syllabus.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert res_file.status_code == 201
    file_data = res_file.get_json()
    assert file_data["resource"]["file"]["original_filename"] == "syllabus.pdf"


def test_api_create_resource_unauthenticated(client):
    res = client.post(
        "/api/resources",
        data={"title": "Test", "description": "Notes"},
    )
    # Login required returns redirect (302) or 401
    assert res.status_code in (302, 401)


def test_cors_preflight_and_headers(client, app):
    app.config["CORS_ALLOWED_ORIGINS"] = ["https://peer-library.vercel.app"]

    # OPTIONS preflight
    preflight = client.options(
        "/api/resources",
        headers={"Origin": "https://peer-library.vercel.app"},
    )
    assert preflight.status_code == 204
    assert (
        preflight.headers.get("Access-Control-Allow-Origin")
        == "https://peer-library.vercel.app"
    )
    assert preflight.headers.get("Access-Control-Allow-Credentials") == "true"

    # Actual GET request
    resp = client.get(
        "/api/resources",
        headers={"Origin": "https://peer-library.vercel.app"},
    )
    assert (
        resp.headers.get("Access-Control-Allow-Origin")
        == "https://peer-library.vercel.app"
    )
    assert resp.headers.get("Access-Control-Allow-Credentials") == "true"

    # Disallowed origin
    resp_disallowed = client.get(
        "/api/resources",
        headers={"Origin": "https://malicious.com"},
    )
    assert "Access-Control-Allow-Origin" not in resp_disallowed.headers
