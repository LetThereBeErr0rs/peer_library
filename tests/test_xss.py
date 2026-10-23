"""Stored-XSS prevention, URL scheme safety and open-redirect guards."""
from extensions import db as _db
from models import Resource
from security import linkify, is_safe_external_url, is_safe_redirect_target


def _add_resource(title, description):
    r = Resource(title=title, description=description, resource_type="notes",
                 author_name="Eve", roll_number="<b>bad</b>", status="published")
    _db.session.add(r)
    _db.session.commit()
    return r


def test_script_in_title_is_escaped_in_html(client):
    _add_resource("<script>alert('xss')</script>", "ok")
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert "<script>alert('xss')</script>" not in body
    assert "&lt;script&gt;" in body


def test_script_in_detail_is_escaped(client):
    r = _add_resource("Safe", "<img src=x onerror=alert(1)>")
    resp = client.get(f"/resource/{r.id}")
    body = resp.get_data(as_text=True)
    assert "<img src=x onerror=alert(1)>" not in body
    assert "&lt;img" in body


def test_api_returns_raw_json_not_markup(client):
    _add_resource("<script>x</script>", "desc")
    resp = client.get("/api/resources")
    assert resp.is_json
    data = resp.get_json()
    # Raw value is preserved in JSON; the browser renders it via textContent.
    assert any("<script>" in r["title"] for r in data["resources"])


def test_linkify_escapes_markup_but_links_http():
    out = str(linkify("see <b>this</b> https://example.com/x?a=1 end"))
    assert "<b>" not in out
    assert "&lt;b&gt;" in out
    assert '<a href="https://example.com/x?a=1"' in out
    assert 'rel="noopener noreferrer"' in out


def test_linkify_ignores_javascript_scheme():
    out = str(linkify("click javascript:alert(1) now"))
    assert "<a" not in out
    assert "javascript:alert(1)" in out  # shown as inert text


def test_is_safe_external_url():
    assert is_safe_external_url("https://example.com")
    assert is_safe_external_url("http://example.com")
    assert not is_safe_external_url("javascript:alert(1)")
    assert not is_safe_external_url("data:text/html,<script>")


def test_open_redirect_guard(app):
    with app.test_request_context("/login"):
        assert is_safe_redirect_target("/contribute")
        assert not is_safe_redirect_target("https://evil.example.com/phish")
        assert not is_safe_redirect_target("//evil.example.com")


def test_security_headers_present(client):
    resp = client.get("/")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in resp.headers
    assert resp.headers.get("X-Frame-Options") == "DENY"
