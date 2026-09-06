from pathlib import Path

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.connection import get_db
from app.database.models import Document
from app.database.models import User
from app.schemas.document import DocumentResponse
from app.services.storage.local_storage import save_file


router = APIRouter(
    prefix="/api/documents",
    tags=["Documents"]
)


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt"
}

@router.post(
    "/upload",
    response_model=DocumentResponse
)
def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    extension = Path(
        file.filename
    ).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Allowed: PDF, DOCX, TXT"
            )
        )

    file_path, file_size = save_file(
        file
    )

    document = Document(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_type=extension,
        file_size=file_size,
        status="uploaded"
    )

    db.add(document)

    db.commit()

    db.refresh(document)

    return document