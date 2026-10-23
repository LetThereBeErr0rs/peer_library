"""Catalogue, search, filtering, pagination and detail routes."""
from extensions import db as _db
from models import Resource
from services import search_resources


def _seed(n=25):
    for i in range(n):
        _db.session.add(Resource(
            title=f"Resource {i:02d}",
            description=f"Content about topic {i}",
            resource_type="notes" if i % 2 else "paper",
            subject="Databases" if i % 3 == 0 else "Networks",
            author_name=f"Author {i}",
            roll_number=f"R{i:03d}",
            status="published" if i != 0 else "hidden",
            download_count=i,
        ))
    _db.session.commit()


def test_homepage_shows_catalogue_without_search(client):
    _seed(5)
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Resource 01" in body


def test_homepage_empty_state(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "No resources found" in resp.get_data(as_text=True)


def test_hidden_not_listed(client):
    _seed(5)
    body = client.get("/").get_data(as_text=True)
    assert "Resource 00" not in body  # hidden


def test_search_partial_title(client):
    _seed(20)
    resp = client.get("/api/resources?q=Resource 1")
    data = resp.get_json()
    assert data["total"] >= 1
    assert all("Resource 1" in r["title"] for r in data["resources"])


def test_search_by_subject_and_author(client):
    _seed(10)
    assert client.get("/api/resources?q=Databases").get_json()["total"] >= 1
    assert client.get("/api/resources?q=Author 3").get_json()["total"] >= 1


def test_filter_by_type(client):
    _seed(10)
    data = client.get("/api/resources?type=paper").get_json()
    assert data["total"] >= 1
    for r in data["resources"]:
        assert r["resource_type"] == "paper"


def test_pagination_boundaries(client):
    _seed(25)
    p1 = client.get("/api/resources?page=1").get_json()
    assert p1["page"] == 1 and p1["has_prev"] is False
    last = client.get(f"/api/resources?page={p1['pages']}").get_json()
    assert last["has_next"] is False


def test_sort_downloads(client):
    _seed(10)
    data = client.get("/api/resources?sort=downloads").get_json()
    counts = [r["download_count"] for r in data["resources"]]
    assert counts == sorted(counts, reverse=True)


def test_missing_detail_404(client):
    assert client.get("/resource/999999").status_code == 404


def test_search_service_case_insensitive(app):
    _seed(5)
    page = search_resources(query="resource 01")
    assert page.total >= 1


def test_static_asset_served(client):
    assert client.get("/static/app.js").status_code == 200
