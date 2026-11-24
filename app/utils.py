import os
from pathlib import Path

from fastapi import UploadFile

UPLOADS = "uploads"
os.makedirs(UPLOADS, exist_ok=True)


def get_upload_path(filename: str | None) -> str:
    if not filename:
        raise ValueError("filename is required")
    # Keep only the final name part so "../../x" cannot write outside UPLOADS.
    return f"{UPLOADS}/{Path(filename).name}"


def save_file(upload_file: UploadFile) -> str:
    """Save an uploaded file into UPLOADS and return the path it was written to."""
    path = get_upload_path(upload_file.filename)
    with open(path, "wb") as f:
        f.write(upload_file.file.read())
    return path
