"""File validation: extensions, size, emptiness, signatures, DOCX structure."""
import io

import pytest
from werkzeug.datastructures import FileStorage

from config import MAX_UPLOAD_BYTES
from validation import read_and_validate, FileValidationError
from conftest import make_pdf, make_png, make_jpeg, make_txt, make_docx


def _fs(data, filename):
    return FileStorage(stream=io.BytesIO(data), filename=filename)


@pytest.mark.parametrize("builder,name,ext", [
    (make_pdf, "notes.pdf", "pdf"),
    (make_png, "diagram.png", "png"),
    (make_jpeg, "scan.jpg", "jpg"),
    (make_jpeg, "scan.jpeg", "jpeg"),
    (make_txt, "notes.txt", "txt"),
    (make_docx, "paper.docx", "docx"),
])
def test_allowed_types_pass(builder, name, ext):
    data, got_ext, mime = read_and_validate(_fs(builder(), name))
    assert got_ext == ext
    assert mime


def test_rejected_extension():
    with pytest.raises(FileValidationError):
        read_and_validate(_fs(b"MZ...", "malware.exe"))


def test_no_filename():
    with pytest.raises(FileValidationError):
        read_and_validate(_fs(make_pdf(), ""))


def test_empty_file():
    with pytest.raises(FileValidationError):
        read_and_validate(_fs(b"", "empty.pdf"))


def test_oversized_file():
    big = b"%PDF-1.4\n" + b"0" * (MAX_UPLOAD_BYTES + 10)
    with pytest.raises(FileValidationError):
        read_and_validate(_fs(big, "huge.pdf"))


def test_mime_signature_mismatch_pdf():
    # .pdf extension but PNG bytes.
    with pytest.raises(FileValidationError):
        read_and_validate(_fs(make_png(), "fake.pdf"))


def test_docx_must_be_real_zip():
    with pytest.raises(FileValidationError):
        read_and_validate(_fs(b"not a zip at all", "fake.docx"))


def test_docx_zip_without_office_parts_rejected():
    buf = io.BytesIO()
    import zipfile
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("random.txt", "hello")
    with pytest.raises(FileValidationError):
        read_and_validate(_fs(buf.getvalue(), "fake.docx"))


def test_txt_with_null_bytes_rejected():
    with pytest.raises(FileValidationError):
        read_and_validate(_fs(b"text\x00\x00binary", "notes.txt"))
