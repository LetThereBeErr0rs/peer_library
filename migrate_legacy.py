"""Migrate legacy SQLite ``content`` rows into the new schema.

The legacy database (default: instance/database.db) is treated as a read-only
*source*. It is never modified; a timestamped backup is taken before anything
runs. Rows are mapped into the Resource/ResourceFile schema of the configured
target database (local SQLite by default).

Usage:
    python migrate_legacy.py --dry-run          # preview only, no writes
    python migrate_legacy.py                     # import into the target DB
    python migrate_legacy.py --source other.db   # custom legacy source

Safety:
  * Dry-run is the default-friendly first step and writes nothing.
  * Re-runs are idempotent: a row already present (same title/author/roll/
    description) is skipped, so retries do not create duplicates.
  * A missing attachment (e.g. the dangling ``downloadfile.PDF``) is reported
    and the resource is imported WITHOUT a fabricated file reference.
  * Importing into a non-SQLite (remote) target requires an explicit
    ``--yes`` confirmation.
"""
import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

from app import create_app
from extensions import db
from models import Resource, ResourceFile

LEGACY_DEFAULT = os.path.join("instance", "database.db")


def _looks_like_url(text):
    t = (text or "").strip().lower()
    return t.startswith("http://") or t.startswith("https://")


def _backup(path):
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup = f"{path}.backup.{stamp}.db"
    shutil.copy2(path, backup)
    return backup


def _read_legacy(source):
    conn = sqlite3.connect(source)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, title, name, roll_number, learning_content, file_path "
            "FROM content ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return rows


def _already_imported(title, author, roll, description):
    return (
        Resource.query.filter_by(
            title=title, author_name=author, roll_number=roll, description=description
        ).first()
        is not None
    )


def migrate(source, dry_run=True, upload_folder="uploads"):
    rows = _read_legacy(source)
    report = {
        "total": len(rows),
        "imported": 0,
        "skipped_duplicate": 0,
        "missing_attachment": 0,
        "attached": 0,
        "failures": 0,
    }

    for row in rows:
        title = (row["title"] or "Untitled").strip()
        author = (row["name"] or "").strip() or None
        roll = (row["roll_number"] or "").strip() or None
        description = (row["learning_content"] or "").strip()
        file_path = (row["file_path"] or "").strip() or None

        if _already_imported(title, author, roll, description):
            report["skipped_duplicate"] += 1
            continue

        rtype = "link" if _looks_like_url(description) else "notes"
        resource = Resource(
            title=title,
            description=description,
            resource_type=rtype,
            author_name=author,
            roll_number=roll,
            status="published",
        )

        if file_path:
            disk_path = os.path.join(upload_folder, file_path)
            if os.path.isfile(disk_path):
                size = os.path.getsize(disk_path)
                ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
                resource.files.append(
                    ResourceFile(
                        original_filename=file_path,
                        # Legacy files keep their existing on-disk name as the
                        # storage key (documented exception – we never overwrite
                        # or rename existing uploads).
                        storage_key=file_path,
                        mime_type=_guess_mime(ext),
                        file_size=size,
                        storage_backend="local",
                    )
                )
                report["attached"] += 1
            else:
                # Dangling reference: import the resource, but DO NOT fabricate
                # a file. (Row #1's downloadfile.PDF lands here.)
                report["missing_attachment"] += 1

        if dry_run:
            report["imported"] += 1
            continue

        try:
            db.session.add(resource)
            db.session.commit()
            report["imported"] += 1
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            report["failures"] += 1
            print(f"  ! failed to import legacy row id={row['id']}: {exc}")

    return report


def _guess_mime(ext):
    return {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "txt": "text/plain",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(ext)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Migrate legacy SQLite content.")
    parser.add_argument("--source", default=LEGACY_DEFAULT, help="Legacy SQLite file.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only.")
    parser.add_argument(
        "--yes", action="store_true", help="Confirm import into a non-SQLite target."
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.source):
        print(f"Legacy source not found: {args.source}")
        return 1

    app = create_app()
    with app.app_context():
        target = app.config["SQLALCHEMY_DATABASE_URI"]
        is_sqlite = target.startswith("sqlite")
        if not args.dry_run and not is_sqlite and not args.yes:
            print(
                "Refusing to import into a non-SQLite (remote) target without --yes.\n"
                f"Target: {target.split('@')[-1]}"
            )
            return 2

        # Back up the source before doing anything (even though we only read it).
        backup = _backup(args.source)
        print(f"Backed up legacy source -> {backup}")
        print(f"Target database: {'SQLite (local)' if is_sqlite else target.split('@')[-1]}")
        print(f"Mode: {'DRY RUN (no writes)' if args.dry_run else 'IMPORT'}")
        print("-" * 50)

        report = migrate(args.source, dry_run=args.dry_run, upload_folder=app.config["UPLOAD_FOLDER"])

        print("-" * 50)
        for key, value in report.items():
            print(f"  {key:>20}: {value}")
        if args.dry_run:
            print("\nDry run complete. Re-run without --dry-run to import.")
        else:
            print("\nImport complete. The legacy database was left intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
