"""Database models for Peer Library.

The legacy project had a single ``Content`` table (title, name, roll_number,
learning_content, file_path). Its substance is preserved here:

  * ``title``            -> Resource.title
  * ``learning_content`` -> Resource.description
  * ``name``             -> Resource.author_name (unverified display name)
  * ``roll_number``      -> Resource.roll_number (unverified)
  * ``file_path``        -> a ResourceFile row (when the file still exists)

New tables (User, ResourceFile) add real ownership and file metadata. The
legacy SQLite database is migrated into this schema by migrate_legacy.py; it is
never modified in place.
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Re-export the shared db instance so ``from models import db`` keeps working.
from extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # Self-reported academic identity. Treated as UNVERIFIED – registering does
    # not prove college affiliation (see README "Known limitations").
    roll_number = db.Column(db.String(50), nullable=True)
    department = db.Column(db.String(120), nullable=True)

    role = db.Column(db.String(20), nullable=False, default="student")  # student | admin
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    resources = db.relationship("Resource", back_populates="uploader", lazy="dynamic")

    # --- password helpers ---
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @staticmethod
    def normalize_email(email):
        return (email or "").strip().lower()

    def __repr__(self):
        return f"<User {self.email}>"


class Resource(db.Model):
    __tablename__ = "resources"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False, default="")

    resource_type = db.Column(db.String(40), nullable=False, default="notes", index=True)
    subject = db.Column(db.String(120), nullable=True, index=True)
    category = db.Column(db.String(120), nullable=True, index=True)
    department = db.Column(db.String(120), nullable=True)
    semester = db.Column(db.String(40), nullable=True)

    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    # Display-only author fields. For user-contributed resources these mirror the
    # authenticated uploader; for migrated legacy rows they carry the original,
    # unverified values so no history is lost.
    author_name = db.Column(db.String(120), nullable=True)
    roll_number = db.Column(db.String(50), nullable=True, index=True)

    status = db.Column(db.String(20), nullable=False, default="published", index=True)
    download_count = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    uploader = db.relationship("User", back_populates="resources")
    files = db.relationship(
        "ResourceFile",
        back_populates="resource",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    RESOURCE_TYPES = ("notes", "paper", "book", "syllabus", "link", "other")
    STATUSES = ("published", "pending", "hidden")

    @property
    def primary_file(self):
        return self.files[0] if self.files else None

    @property
    def uploader_name(self):
        if self.uploader:
            return self.uploader.display_name
        return self.author_name or "Unknown"

    def to_dict(self, include_file=True):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "resource_type": self.resource_type,
            "subject": self.subject,
            "category": self.category,
            "department": self.department,
            "semester": self.semester,
            "uploader_name": self.uploader_name,
            "roll_number": self.roll_number,
            "status": self.status,
            "download_count": self.download_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_file:
            pf = self.primary_file
            data["file"] = pf.to_dict() if pf else None
        return data

    def __repr__(self):
        return f"<Resource {self.id} {self.title!r}>"


class ResourceFile(db.Model):
    __tablename__ = "resource_files"

    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(
        db.Integer, db.ForeignKey("resources.id"), nullable=False, index=True
    )

    original_filename = db.Column(db.String(255), nullable=False)
    # Randomized, server-generated key (UUID-based) for new uploads, so keys do
    # not collide. Not globally unique at the DB level because several migrated
    # legacy resources may legitimately reference the same shared on-disk file.
    storage_key = db.Column(db.String(255), nullable=False, index=True)
    mime_type = db.Column(db.String(120), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    storage_backend = db.Column(db.String(20), nullable=False, default="local")
    bucket = db.Column(db.String(120), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    resource = db.relationship("Resource", back_populates="files")

    def to_dict(self):
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "storage_backend": self.storage_backend,
        }

    def __repr__(self):
        return f"<ResourceFile {self.id} {self.original_filename!r}>"
