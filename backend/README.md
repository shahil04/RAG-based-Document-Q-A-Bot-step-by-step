# Step 3 — Document Upload System

Now we start the **actual RAG pipeline**.

Our goal in this step is **only document upload and document metadata**.

We will support:

* PDF
* DOCX
* TXT

Development storage:

```text
backend/uploads/
```

Production storage later:

```text
AWS S3
```

Metadata:

```text
Supabase PostgreSQL
```

We will **not process embeddings or Pinecone yet**. That comes after upload is working.

---

# 3.1 Architecture

```text
                    React
                      │
                      │ PDF / DOCX / TXT
                      ▼
                  FastAPI
                      │
                      ▼
                JWT Authentication
                      │
                      ▼
              Document Upload API
                      │
              ┌───────┴────────┐
              ▼                ▼
        Local Storage       Supabase
        uploads/            PostgreSQL
              │                │
              │                ▼
              │             documents
              │
              ▼
         Next Step:
      Document Processing
```

Later:

```text
Document
   ↓
Text Extraction
   ↓
Chunking
   ↓
Embeddings
   ↓
Pinecone
```

---

# 3.2 Install Upload Dependency

FastAPI needs `python-multipart` for file uploads.

Run:

```bash
uv add python-multipart
```

---

# 3.3 Update Project Structure

Add these files:

```text
backend/
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── health.py
│   │   └── documents.py       ← NEW
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   └── models.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   └── document.py        ← NEW
│   │
│   └── services/
│       ├── __init__.py
│       └── storage/
│           ├── __init__.py
│           └── local_storage.py ← NEW
│
├── uploads/                     ← NEW
│
├── .env
├── .gitignore
├── pyproject.toml
└── uv.lock
```

---

# 3.4 Create `documents` Database Model

Our users already exist in Supabase.

Now we need:

```text
documents
```

Create/update:

```text
app/database/models.py
```

```python
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.sql import func

from app.database.connection import Base


class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )


class Document(Base):

    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    filename = Column(
        String(255),
        nullable=False
    )

    file_path = Column(
        String(500),
        nullable=False
    )

    file_type = Column(
        String(50),
        nullable=False
    )

    file_size = Column(
        Integer,
        nullable=False
    )

    status = Column(
        String(50),
        default="uploaded",
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
```

---

# 3.5 Understand the Relationship

We now have:

```text
users
────────────────
id
name
email
password_hash
created_at


documents
────────────────
id
user_id  ───────────────┐
filename                │
file_path               │
file_type               │
file_size               │
status                  │
created_at              │
                        │
                        ▼
                     users.id
```

This means:

> One user can have many documents.

For example:

```text
Rahul
  │
  ├── python.pdf
  ├── machine-learning.pdf
  └── fastapi.pdf
```

---

# 3.6 Important: Database Migration

Because the `users` table may already exist, `create_all()` will create the new `documents` table but won't modify existing tables.

For our beginner project, we can temporarily continue with:

```python
Base.metadata.create_all(bind=engine)
```

Later, before production deployment, we'll introduce:

```text
Alembic
```

for proper database migrations.

---

# 3.7 Create Document Schema

Create:

```text
app/schemas/document.py
```

```python
from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):

    id: int
    filename: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
```

The API won't expose:

```text
password
internal filesystem information
```

---

# 3.8 Create Local Storage Service

This is an important architectural decision.

Don't put file-saving logic directly inside the API route.

Create:

```text
app/services/storage/local_storage.py
```

```python
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
```

---

# 3.9 Why UUID?

Suppose two users upload:

```text
python.pdf
```

If we save directly:

```text
uploads/python.pdf
```

the second upload could overwrite the first.

Instead:

```text
uploads/
├── 7c7e2c3e-....pdf
├── 1a8f93ab-....pdf
└── 9f3a7c12-....pdf
```

The original filename remains in PostgreSQL:

```text
filename = python.pdf
```

---

# 3.10 Create Document API

Create:

```text
app/api/documents.py
```

```python
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
```

---

# 3.11 Upload Endpoint

Add:

```python
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
```

---

# 3.12 Connect Router

Update:

```text
app/main.py
```

Add:

```python
from app.api.documents import router as documents_router
```

Then:

```python
app.include_router(
    documents_router
)
```

Complete relevant section:

```python
app.include_router(
    health_router
)

app.include_router(
    auth_router
)

app.include_router(
    documents_router
)
```

---

# 3.13 Start Server

```bash
uv run fastapi dev app/main.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

You should now see:

```text
Authentication
    POST /api/auth/register
    POST /api/auth/login
    GET  /api/auth/me

Documents
    POST /api/documents/upload
```

---

# 3.14 Test Upload

First:

```text
POST /api/auth/login
```

Get the JWT.

Then click:

```text
Authorize
```

Enter:

```text
Bearer YOUR_TOKEN
```

Now select:

```text
POST /api/documents/upload
```

Click:

```text
Try it out
```

Choose a file:

```text
python.pdf
```

Execute.

Response:

```json
{
    "id": 1,
    "filename": "python.pdf",
    "file_type": ".pdf",
    "file_size": 245678,
    "status": "uploaded",
    "created_at": "2026-09-06T..."
}
```

---

# 3.15 Check Local Folder

Your project should now contain:

```text
backend/
│
├── uploads/
│   └── 7b3d91c2-....pdf
│
├── app/
│
└── ...
```

And Supabase:

```text
documents
────────────────────────────
id
user_id
filename
file_path
file_type
file_size
status
created_at
```

For example:

```text
id          1
user_id     1
filename    python.pdf
file_path   uploads/7b3d91c2....pdf
file_type   .pdf
file_size   245678
status      uploaded
```

---

# 3.16 Why Store Metadata in Supabase?

We **don't** want to store the actual PDF inside PostgreSQL.

Instead:

```text
                  Document
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
       File                  Metadata
          │                     │
          ▼                     ▼
     Local / S3              Supabase
```

For example:

```text
S3:
documents/user-1/abc123.pdf
```

Supabase:

```text
document_id = 1
user_id = 1
filename = python.pdf
storage_key = documents/user-1/abc123.pdf
status = uploaded
```

This separation becomes important when we have thousands of documents.

---

# 3.17 Better Production Design

Our current local storage:

```text
save_file()
     ↓
uploads/
```

will later become:

```text
                 Storage Service
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
      LocalStorage            S3Storage
            │                     │
            ▼                     ▼
        uploads/                AWS S3
```

We'll create a common interface later:

```text
StorageService
      │
      ├── LocalStorage
      │
      └── S3Storage
```

Then your document API doesn't need to know whether it's using local disk or S3.

---

# 3.18 Add File Size Protection

We should also prevent someone from uploading a huge file.

For example:

```python
MAX_FILE_SIZE = 20 * 1024 * 1024
```

That's:

```text
20 MB
```

Modify the upload route:

```python
MAX_FILE_SIZE = 20 * 1024 * 1024
```

After saving:

```python
if file_size > MAX_FILE_SIZE:

    raise HTTPException(
        status_code=400,
        detail="File size cannot exceed 20 MB"
    )
```

However, there's a problem with this simple approach: the file has already been written to disk.

A better production implementation will **stream the upload and enforce the limit while writing**. We'll improve the storage service when we harden the project.

For the beginner version, the current approach is enough to understand the architecture.

---

# 3.19 Current RAG Project Progress

We now have:

```text
                         RAG APPLICATION
                               │
              ┌────────────────┴────────────────┐
              │                                 │
           Frontend                          Backend
           React.js                          FastAPI
                                                │
                        ┌───────────────────────┼───────────────┐
                        │                       │               │
                        ▼                       ▼               ▼
                   Authentication          Documents       Future Chat
                        │                       │
                        ▼                       ▼
                   Supabase                Local/S3
                   PostgreSQL              Storage
                        │
                        ▼
                      Users
```

And the document pipeline will become:

```text
             PDF / DOCX / TXT
                     │
                     ▼
                FastAPI Upload
                     │
                     ▼
               Local / S3
                     │
                     ▼
              Document Record
                     │
                     ▼
             Text Extraction
                     │
                     ▼
                  Chunking
                     │
                     ▼
                Embeddings
                     │
                     ▼
                 Pinecone
                     │
                     ▼
              Semantic Search
                     │
                     ▼
                LangGraph
                     │
                     ▼
                   Groq
                     │
                     ▼
                  Answer
```

---

# Step 3 Complete ✅

At this point:

```text
✅ FastAPI
✅ uv
✅ Supabase PostgreSQL
✅ User registration
✅ User login
✅ JWT authentication
✅ Protected API
✅ Document upload
✅ Local document storage
✅ Document metadata
```

We have **not yet used Pinecone, LangChain, LangGraph, or Groq**. That's intentional—we're building the system incrementally so each component has a clear purpose.

## Next — Step 4: Document Processing

Now we'll take:

```text
uploads/python.pdf
```

and build:

```text
PDF
 ↓
PyPDFLoader
 ↓
Document pages
 ↓
Text cleaning
 ↓
RecursiveCharacterTextSplitter
 ↓
Chunks
```

Then we'll introduce **LangChain** properly and store processing status in Supabase:

```text
uploaded
   ↓
processing
   ↓
processed
   ↓
embedded
```

After that comes **Step 5: Embeddings + Pinecone**.