"""Upload lifecycle, storage keys, downloads and failure cleanup."""
import os

import pytest

from extensions import db as _db
from models import Resource, ResourceFile
from services import create_resource
from storage import LocalStorage, StorageError, generate_storage_key
from validation import FileValidationError
from conftest import make_pdf, make_png, upload_tuple


def _form(**over):
    base = {"title": "My Notes", "description": "Some content",
            "resource_type": "notes", "subject": "", "category": "",
            "semester": "", "department": ""}
    base.update(over)
    return base


def test_upload_generates_random_storage_key(client, make_user, login, app):
    make_user()
    login()
    data = {**_form(), "file": upload_tuple(make_pdf(), "original name.pdf")}
    resp = client.post("/contribute", data=data, content_type="multipart/form-data",
                       follow_redirects=True)
    assert resp.status_code == 200
    rf = ResourceFile.query.first()
    assert rf is not None
    assert rf.original_filename == "original name.pdf"   # preserved as metadata
    assert rf.storage_key != "original name.pdf"          # NOT the user filename
    assert rf.storage_key.endswith(".pdf")
    # File physically stored under the random key.
    assert os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], rf.storage_key))


def test_rejected_file_does_not_create_resource(client, make_user, login):
    make_user()
    login()
    data = {**_form(), "file": upload_tuple(b"MZ", "x.exe")}
    resp = client.post("/contribute", data=data, content_type="multipart/form-data")
    # FileAllowed on the form rejects .exe before our handler (400).
    assert resp.status_code in (400,)
    assert Resource.query.count() == 0


def test_signature_mismatch_rejected(client, make_user, login):
    make_user()
    login()
    data = {**_form(), "file": upload_tuple(make_png(), "fake.pdf")}
    resp = client.post("/contribute", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert Resource.query.count() == 0


def test_resource_without_file(client, make_user, login):
    make_user()
    login()
    resp = client.post("/contribute", data=_form(title="No file"),
                       content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200
    r = Resource.query.filter_by(title="No file").first()
    assert r is not None
    assert r.primary_file is None


def test_duplicate_original_filenames_allowed(client, make_user, login, app):
    make_user()
    login()
    for _ in range(2):
        client.post("/contribute",
                    data={**_form(), "file": upload_tuple(make_pdf(), "same.pdf")},
                    content_type="multipart/form-data", follow_redirects=True)
    files = ResourceFile.query.filter_by(original_filename="same.pdf").all()
    assert len(files) == 2
    assert files[0].storage_key != files[1].storage_key  # distinct random keys


def test_db_failure_cleans_up_stored_object(app, make_user, monkeypatch):
    """If the DB commit fails, the just-stored file must be removed."""
    with app.app_context():
        user = make_user()

        # Force the commit to fail after the file is stored.
        import services
        real_commit = _db.session.commit

        def boom():
            raise RuntimeError("db exploded")

        monkeypatch.setattr(_db.session, "commit", boom)

        from werkzeug.datastructures import FileStorage
        import io
        fs = FileStorage(stream=io.BytesIO(make_pdf()), filename="x.pdf")

        with pytest.raises(RuntimeError):
            create_resource(form_data=_form(), uploader=user, file_storage=fs)

        monkeypatch.setattr(_db.session, "commit", real_commit)
        # No orphaned file should remain.
        folder = app.config["UPLOAD_FOLDER"]
        remaining = os.listdir(folder) if os.path.isdir(folder) else []
        assert remaining == []


def test_download_missing_file_returns_410(client, make_user, login, app):
    make_user()
    login()
    client.post("/contribute",
                data={**_form(), "file": upload_tuple(make_pdf(), "x.pdf")},
                content_type="multipart/form-data", follow_redirects=True)
    rf = ResourceFile.query.first()
    # Remove the physical file to simulate a dangling reference.
    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], rf.storage_key))
    resp = client.get(f"/download/{rf.id}")
    assert resp.status_code == 410


def test_download_unknown_id_404(client):
    assert client.get("/download/99999").status_code == 404


def test_download_increments_count(client, make_user, login):
    make_user()
    login()
    client.post("/contribute",
                data={**_form(), "file": upload_tuple(make_pdf(), "x.pdf")},
                content_type="multipart/form-data", follow_redirects=True)
    rf = ResourceFile.query.first()
    before = rf.resource.download_count
    client.get(f"/download/{rf.id}")
    assert _db.session.get(Resource, rf.resource_id).download_count == before + 1


def test_hidden_resource_download_forbidden_for_anon(client, make_user, login, app):
    make_user()
    login()
    client.post("/contribute",
                data={**_form(), "file": upload_tuple(make_pdf(), "x.pdf")},
                content_type="multipart/form-data", follow_redirects=True)
    rf = ResourceFile.query.first()
    rf.resource.status = "hidden"
    _db.session.commit()
    client.post("/logout", follow_redirects=True)
    assert client.get(f"/download/{rf.id}").status_code == 403


def test_local_storage_rejects_traversal(tmp_path):
    store = LocalStorage(str(tmp_path))
    with pytest.raises(StorageError):
        store._path("../../etc/passwd")
