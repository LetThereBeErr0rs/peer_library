"""Legacy data migration: mapping, idempotency, missing/shared attachments."""
import os
import sqlite3

import pytest

import migrate_legacy
from models import Resource, ResourceFile


@pytest.fixture
def legacy_db(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE content (id INTEGER PRIMARY KEY, title TEXT, name TEXT, "
        "roll_number TEXT, learning_content TEXT, file_path TEXT)"
    )
    rows = [
        (1, "yt", "xyz", "200", "https://youtu.be/abc", "missing.PDF"),
        (2, "shared a", "pqr", "100", "note a", "logo.png"),
        (3, "no file", "sql", "890", "plain text", None),
        (4, "shared b", "sam", "123", "note b", "logo.png"),
    ]
    conn.executemany("INSERT INTO content VALUES (?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return str(path)


def test_dry_run_writes_nothing(app, legacy_db):
    report = migrate_legacy.migrate(legacy_db, dry_run=True,
                                    upload_folder=app.config["UPLOAD_FOLDER"])
    assert report["total"] == 4
    assert report["imported"] == 4
    assert Resource.query.count() == 0  # nothing persisted


def test_import_maps_fields_and_type(app, legacy_db):
    migrate_legacy.migrate(legacy_db, dry_run=False,
                           upload_folder=app.config["UPLOAD_FOLDER"])
    yt = Resource.query.filter_by(title="yt").first()
    assert yt.resource_type == "link"         # URL content -> link
    assert yt.author_name == "xyz"
    assert yt.roll_number == "200"
    assert yt.primary_file is None            # dangling attachment, not fabricated

    plain = Resource.query.filter_by(title="no file").first()
    assert plain.resource_type == "notes"


def test_missing_attachment_reported(app, legacy_db):
    # No physical files exist in this test's upload folder, so every row that
    # references a file (1, 2, 4) counts as a missing attachment.
    report = migrate_legacy.migrate(legacy_db, dry_run=False,
                                    upload_folder=app.config["UPLOAD_FOLDER"])
    assert report["missing_attachment"] == 3
    assert ResourceFile.query.count() == 0  # nothing fabricated


def test_shared_filename_handled(app, legacy_db):
    # Create the shared physical file so both rows attach it.
    folder = app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "logo.png"), "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
    report = migrate_legacy.migrate(legacy_db, dry_run=False, upload_folder=folder)
    assert report["attached"] == 2
    assert report["failures"] == 0
    files = ResourceFile.query.filter_by(original_filename="logo.png").all()
    assert len(files) == 2


def test_idempotent_rerun(app, legacy_db):
    folder = app.config["UPLOAD_FOLDER"]
    migrate_legacy.migrate(legacy_db, dry_run=False, upload_folder=folder)
    first = Resource.query.count()
    report = migrate_legacy.migrate(legacy_db, dry_run=False, upload_folder=folder)
    assert report["skipped_duplicate"] == 4
    assert Resource.query.count() == first   # no duplicates
