"""Server-side upload validation.

Validation never trusts the browser. We check, in order:
  1. a non-empty filename with an allowed extension,
  2. the declared size against the 25 MiB limit and against emptiness,
  3. the actual leading bytes (magic number) of the file.

The HTML ``accept`` attribute is a convenience only and is never relied upon.
"""
import io
import zipfile

from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES


class FileValidationError(Exception):
    """Raised when an uploaded file fails a validation rule."""


# Minimal, declared MIME types we are willing to serve back.
EXTENSION_MIME = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "txt": "text/plain",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def extension_of(filename):
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].strip().lower()


def _looks_like_pdf(head):
    return head[:5] == b"%PDF-"


def _looks_like_png(head):
    return head[:8] == b"\x89PNG\r\n\x1a\n"


def _looks_like_jpeg(head):
    return head[:3] == b"\xff\xd8\xff"


def _looks_like_zip(head):
    # DOCX is an Office Open XML ZIP container.
    return head[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


def _is_probably_text(sample):
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        # Allow common single-byte encodings rather than rejecting plain notes.
        return all(b >= 0x09 for b in sample)


def _signature_ok(ext, data):
    head = data[:16]
    if ext == "pdf":
        return _looks_like_pdf(head)
    if ext == "png":
        return _looks_like_png(head)
    if ext in ("jpg", "jpeg"):
        return _looks_like_jpeg(head)
    if ext == "txt":
        return _is_probably_text(data[:4096])
    if ext == "docx":
        if not _looks_like_zip(head):
            return False
        return _docx_structure_ok(data)
    return False


def _docx_structure_ok(data):
    """A real .docx is a ZIP that contains ``[Content_Types].xml`` and word/."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
            if "[Content_Types].xml" not in names:
                return False
            return any(n.startswith("word/") for n in names)
    except (zipfile.BadZipFile, OSError):
        return False


def read_and_validate(file_storage):
    """Validate a Werkzeug FileStorage and return its bytes.

    Returns ``(data, extension, mime_type)`` on success, raising
    ``FileValidationError`` with a user-safe message otherwise.
    """
    filename = (file_storage.filename or "").strip()
    if not filename:
        raise FileValidationError("No file was provided.")

    ext = extension_of(filename)
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise FileValidationError(
            f"File type '.{ext or '?'}' is not allowed. Allowed types: {allowed}."
        )

    # Read fully but cap at the limit + 1 byte so we can detect oversize without
    # loading unbounded data.
    data = file_storage.read(MAX_UPLOAD_BYTES + 1)
    try:
        file_storage.stream.seek(0)
    except (OSError, ValueError):
        pass

    if len(data) == 0:
        raise FileValidationError("The file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        mib = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise FileValidationError(f"The file is larger than the {mib} MiB limit.")

    if not _signature_ok(ext, data):
        raise FileValidationError(
            f"The file contents do not match a valid .{ext} file."
        )

    return data, ext, EXTENSION_MIME[ext]
