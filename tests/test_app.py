"""Application startup, configuration validation and error handling."""
import pytest

from app import create_app
from config import Config, TestConfig


def test_app_imports_and_has_routes(app):
    rules = {r.rule for r in app.url_map.iter_rules()}
    for expected in ("/", "/api/resources", "/contribute", "/login", "/register",
                     "/download/<int:file_id>"):
        assert expected in rules


def test_production_requires_secret_key(monkeypatch):
    app = create_app(TestConfig)
    app.config["ENV"] = "production"
    app.config["SECRET_KEY"] = "dev-insecure-change-me"
    with pytest.raises(RuntimeError):
        Config.validate_production(app)


def test_production_rejects_sqlite(monkeypatch):
    app = create_app(TestConfig)
    app.config["ENV"] = "production"
    app.config["SECRET_KEY"] = "a-strong-secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///x.db"
    with pytest.raises(RuntimeError):
        Config.validate_production(app)


def test_production_requires_supabase_when_selected():
    app = create_app(TestConfig)
    app.config["ENV"] = "production"
    app.config["SECRET_KEY"] = "a-strong-secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://u:p@h/db"
    app.config["STORAGE_BACKEND"] = "supabase"
    app.config["SUPABASE_URL"] = None
    with pytest.raises(RuntimeError):
        Config.validate_production(app)


def test_404_renders_error_page(client):
    resp = client.get("/no-such-page")
    assert resp.status_code == 404
    assert "could not be found" in resp.get_data(as_text=True)


def test_api_404_returns_json(client):
    resp = client.get("/api/resources/nope")
    assert resp.status_code == 404


def test_db_url_normalization():
    from config import _normalize_db_url
    assert _normalize_db_url("postgres://u:p@h/db").startswith("postgresql+psycopg://")
    assert _normalize_db_url("postgresql://u:p@h/db").startswith("postgresql+psycopg://")
