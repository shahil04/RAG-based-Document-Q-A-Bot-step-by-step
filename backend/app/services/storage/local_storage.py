from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


UPLOAD_DIR = Path("uploads")


def save_file(
    file: UploadFile
) -> tuple[str, int]:

    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    extension = Path(
        file.filename
    ).suffix.lower()

    unique_filename = (
        f"{uuid4()}{extension}"
    )

    file_path = (
        UPLOAD_DIR / unique_filename
    )

    content = file.file.read()

    file_path.write_bytes(content)

    file_size = len(content)

    return str(file_path), file_size