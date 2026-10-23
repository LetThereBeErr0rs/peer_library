"""Authorization regression tests for the resource detail page.

Published resources are public; pending/hidden resources must only be visible to
their owner and to administrators. Unauthorized visitors get a non-disclosing
404 (never the title/description).
"""
import pytest

from extensions import db as _db
from models import Resource


def _make_resource(owner, status, title="Secret Title", description="Secret body"):
    r = Resource(title=title, description=description, resource_type="notes",
                 status=status, uploader_id=owner.id, author_name=owner.display_name)
    _db.session.add(r)
    _db.session.commit()
    return r


@pytest.fixture
def owner(make_user):
    return make_user(email="owner@example.com", password="password123",
                     display_name="Owner")


@pytest.fixture
def other(make_user):
    return make_user(email="other@example.com", password="password123",
                     display_name="Other")


@pytest.fixture
def admin(make_user):
    return make_user(email="admin@example.com", password="password123",
                     display_name="Admin", role="admin")


# ---- Published: public to everyone ----
def test_published_visible_to_anonymous(client, owner):
    r = _make_resource(owner, "published")
    resp = client.get(f"/resource/{r.id}")
    assert resp.status_code == 200
    assert "Secret Title" in resp.get_data(as_text=True)


# ---- Pending: restricted ----
@pytest.mark.parametrize("status", ["pending", "hidden"])
def test_restricted_hidden_from_anonymous(client, owner, status):
    r = _make_resource(owner, status)
    resp = client.get(f"/resource/{r.id}")
    assert resp.status_code == 404
    body = resp.get_data(as_text=True)
    assert "Secret Title" not in body      # no metadata disclosure
    assert "Secret body" not in body


@pytest.mark.parametrize("status", ["pending", "hidden"])
def test_restricted_hidden_from_unrelated_user(client, owner, other, login, status):
    r = _make_resource(owner, status)
    login("other@example.com", "password123")
    resp = client.get(f"/resource/{r.id}")
    assert resp.status_code == 404
    assert "Secret Title" not in resp.get_data(as_text=True)


@pytest.mark.parametrize("status", ["pending", "hidden"])
def test_restricted_visible_to_owner(client, owner, login, status):
    r = _make_resource(owner, status)
    login("owner@example.com", "password123")
    resp = client.get(f"/resource/{r.id}")
    assert resp.status_code == 200
    assert "Secret Title" in resp.get_data(as_text=True)


@pytest.mark.parametrize("status", ["pending", "hidden"])
def test_restricted_visible_to_admin(client, owner, admin, login, status):
    r = _make_resource(owner, status)
    login("admin@example.com", "password123")
    resp = client.get(f"/resource/{r.id}")
    assert resp.status_code == 200
    assert "Secret Title" in resp.get_data(as_text=True)


def test_missing_resource_404(client):
    assert client.get("/resource/999999").status_code == 404


def test_id_guessing_does_not_leak_restricted(client, owner):
    # A restricted resource sits between two published ones; guessing its id
    # must not reveal it.
    _make_resource(owner, "published", title="Pub One")
    secret = _make_resource(owner, "pending", title="Hidden Two")
    _make_resource(owner, "published", title="Pub Three")
    resp = client.get(f"/resource/{secret.id}")
    assert resp.status_code == 404
    assert "Hidden Two" not in resp.get_data(as_text=True)
