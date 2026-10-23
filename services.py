"""Business logic: resource querying and the upload lifecycle.

Keeping this out of the route handlers makes both easier to test and keeps the
transactional ordering (validate -> store -> persist -> clean up on failure) in
one reviewed place.
"""
import logging

from sqlalchemy import or_, desc, asc

from extensions import db
from models import Resource, ResourceFile
from storage import get_storage, generate_storage_key, StorageError
from validation import read_and_validate, FileValidationError

log = logging.getLogger(__name__)

SORT_OPTIONS = {
    "newest": lambda q: q.order_by(desc(Resource.created_at)),
    "oldest": lambda q: q.order_by(asc(Resource.created_at)),
    "downloads": lambda q: q.order_by(desc(Resource.download_count)),
    "title": lambda q: q.order_by(asc(Resource.title)),
}


def search_resources(
    *,
    query=None,
    resource_type=None,
    subject=None,
    category=None,
    semester=None,
    sort="newest",
    page=1,
    per_page=12,
    include_hidden=False,
):
    """Return a paginated, filtered set of resources.

    Uses safe ORM queries with case-insensitive partial matching that works on
    both SQLite and PostgreSQL. Never loads the whole table into memory.
    """
    q = Resource.query
    if not include_hidden:
        q = q.filter(Resource.status == "published")

    if query:
        like = f"%{query.strip()}%"
        q = q.filter(
            or_(
                Resource.title.ilike(like),
                Resource.description.ilike(like),
                Resource.subject.ilike(like),
                Resource.category.ilike(like),
                Resource.author_name.ilike(like),
                Resource.roll_number.ilike(like),
                Resource.resource_type.ilike(like),
            )
        )
    if resource_type:
        q = q.filter(Resource.resource_type == resource_type)
    if subject:
        q = q.filter(Resource.subject.ilike(f"%{subject.strip()}%"))
    if category:
        q = q.filter(Resource.category.ilike(f"%{category.strip()}%"))
    if semester:
        q = q.filter(Resource.semester == semester)

    sort_fn = SORT_OPTIONS.get(sort, SORT_OPTIONS["newest"])
    q = sort_fn(q)

    per_page = max(1, min(int(per_page), 60))
    page = max(1, int(page))
    return q.paginate(page=page, per_page=per_page, error_out=False)


def create_resource(*, form_data, uploader, file_storage=None):
    """Create a resource, optionally with one attached file.

    Lifecycle:
      1. validate metadata (done by the form before this call),
      2. validate the file,
      3. store the file under a random key,
      4. persist resource + file metadata in one DB transaction,
      5. on DB failure, delete the just-stored object so no orphan remains.

    Returns the created Resource. Raises FileValidationError or StorageError
    with user-safe messages.
    """
    resource = Resource(
        title=form_data["title"].strip(),
        description=form_data["description"].strip(),
        resource_type=form_data.get("resource_type") or "notes",
        subject=(form_data.get("subject") or "").strip() or None,
        category=(form_data.get("category") or "").strip() or None,
        semester=(form_data.get("semester") or "").strip() or None,
        department=(form_data.get("department") or "").strip() or None,
        uploader_id=uploader.id,
        author_name=uploader.display_name,
        roll_number=uploader.roll_number,
        status="published",
    )

    stored_key = None
    storage = None
    resource_file = None

    if file_storage and (file_storage.filename or "").strip():
        # (2) validate before persisting anything.
        data, ext, mime = read_and_validate(file_storage)
        # (3) store under a random key.
        storage = get_storage()
        stored_key = generate_storage_key(ext)
        storage.save(stored_key, data, mime_type=mime)
        resource_file = ResourceFile(
            original_filename=file_storage.filename.strip()[:255],
            storage_key=stored_key,
            mime_type=mime,
            file_size=len(data),
            storage_backend=storage.backend_name,
            bucket=getattr(storage, "bucket", None),
        )
        resource.files.append(resource_file)

    # (4) persist.
    try:
        db.session.add(resource)
        db.session.commit()
    except Exception:
        db.session.rollback()
        # (5) compensating cleanup for the stored object.
        if storage is not None and stored_key is not None:
            try:
                storage.delete(stored_key)
            except Exception:
                log.warning("Failed to clean up orphaned object %s", stored_key)
        raise

    return resource


def register_download(resource):
    """Increment the download counter (best-effort, never blocks a download)."""
    try:
        resource.download_count = (resource.download_count or 0) + 1
        db.session.commit()
    except Exception:
        db.session.rollback()
        log.warning("Could not record download for resource %s", resource.id)
