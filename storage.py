"""Storage abstraction.

Two backends share one interface so the rest of the app never cares where a
file physically lives:

  * ``LocalStorage``    – files under UPLOAD_FOLDER. A deliberate *development*
                          option; not for production (container filesystems are
                          ephemeral).
  * ``SupabaseStorage`` – a private Supabase Storage bucket. Downloads are
                          served via short-lived signed URLs.

Storage keys are always server-generated (UUID + extension); user input never
decides a filesystem path or bucket name.
"""
import os
import uuid

from flask import current_app, send_file


class StorageError(Exception):
    """Raised for backend failures (missing object, provider error, etc.)."""


def generate_storage_key(extension):
    ext = (extension or "").lstrip(".").lower()
    return f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex


class LocalStorage:
    backend_name = "local"

    def __init__(self, folder):
        self.folder = os.path.abspath(folder)
        os.makedirs(self.folder, exist_ok=True)

    def _path(self, storage_key):
        # Guard against traversal: the resolved path must stay inside folder.
        safe = os.path.abspath(os.path.join(self.folder, storage_key))
        if os.path.commonpath([self.folder, safe]) != self.folder:
            raise StorageError("Invalid storage key.")
        return safe

    def save(self, storage_key, data, mime_type=None):
        path = self._path(storage_key)
        if os.path.exists(path):
            # Never overwrite an existing object (keys are random, so this is a
            # genuine collision – regenerate rather than clobber).
            raise StorageError("Storage key already exists.")
        with open(path, "wb") as fh:
            fh.write(data)
        return storage_key

    def exists(self, storage_key):
        try:
            return os.path.isfile(self._path(storage_key))
        except StorageError:
            return False

    def delete(self, storage_key):
        try:
            path = self._path(storage_key)
        except StorageError:
            return
        if os.path.isfile(path):
            os.remove(path)

    def send(self, storage_key, download_name, mime_type=None):
        """Return a Flask response streaming the file as an attachment."""
        path = self._path(storage_key)
        if not os.path.isfile(path):
            raise StorageError("File not found.")
        return send_file(
            path,
            mimetype=mime_type or "application/octet-stream",
            as_attachment=True,
            download_name=download_name,
        )


class SupabaseStorage:
    backend_name = "supabase"

    def __init__(self, url, service_key, bucket, signed_url_ttl=120):
        self.bucket = bucket
        self.signed_url_ttl = signed_url_ttl
        try:
            from supabase import create_client
        except ImportError as exc:  # pragma: no cover - import guard
            raise StorageError(
                "The 'supabase' package is required for STORAGE_BACKEND=supabase."
            ) from exc
        self._client = create_client(url, service_key)

    def _store(self):
        return self._client.storage.from_(self.bucket)

    def save(self, storage_key, data, mime_type=None):
        try:
            self._store().upload(
                storage_key,
                data,
                {"content-type": mime_type or "application/octet-stream"},
            )
        except Exception as exc:  # supabase raises provider-specific errors
            raise StorageError(f"Upload to Supabase failed: {exc}") from exc
        return storage_key

    def exists(self, storage_key):
        try:
            self._store().create_signed_url(storage_key, 10)
            return True
        except Exception:
            return False

    def delete(self, storage_key):
        try:
            self._store().remove([storage_key])
        except Exception:
            # Best-effort cleanup; caller logs the orphan.
            pass

    def signed_url(self, storage_key):
        try:
            res = self._store().create_signed_url(storage_key, self.signed_url_ttl)
        except Exception as exc:
            raise StorageError(f"Could not create signed URL: {exc}") from exc
        url = res.get("signedURL") or res.get("signed_url")
        if not url:
            raise StorageError("Supabase did not return a signed URL.")
        return url

    def send(self, storage_key, download_name, mime_type=None):
        # Callers that support redirects use signed_url(); send() is provided for
        # interface symmetry by redirecting to the signed URL.
        from flask import redirect

        return redirect(self.signed_url(storage_key))


def get_storage():
    """Build the configured storage backend from the current app config."""
    backend = current_app.config.get("STORAGE_BACKEND", "local")
    if backend == "supabase":
        return SupabaseStorage(
            url=current_app.config["SUPABASE_URL"],
            service_key=current_app.config["SUPABASE_SERVICE_KEY"],
            bucket=current_app.config["SUPABASE_BUCKET"],
            signed_url_ttl=current_app.config.get("SUPABASE_SIGNED_URL_TTL", 120),
        )
    return LocalStorage(current_app.config["UPLOAD_FOLDER"])
