

# Step 2 — Supabase PostgreSQL Authentication

Yes. Let's redo Step 2 correctly using **Supabase PostgreSQL** from the beginning.

We will build:

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

Architecture:

```text
React.js
   │
   │ HTTP
   ▼
FastAPI
   │
   ├── JWT Authentication
   │
   ▼
SQLAlchemy
   │
   ▼
Supabase PostgreSQL
   │
   └── users
```

For this project, **Supabase is our managed PostgreSQL database**. We are not using SQLite.

---

# 2.1 Create Supabase Project

Go to [Supabase](https://supabase.com/?utm_source=chatgpt.com) and create a project.

You will need:

```text
Project Name
Database Password
Region
```

For an India-based deployment, choose the region closest to your users when available.

After the project is created, open:

```text
Supabase Dashboard
       ↓
Project Settings
       ↓
Database
       ↓
Connection string

use the pooler string 
DATABASE_URL=postgresql://postgres.wnhroarxwhcjowwljbub:[password]@ap-southeast-2.pooler.supabase.com:5432/postgres

```

We will use the PostgreSQL connection string.

It will look conceptually like:

```text
postgresql://postgres:PASSWORD@HOST:5432/postgres
```

**Do not paste your actual database password or connection string into the chat.**

---

# 2.2 Install PostgreSQL Dependencies

From your `backend` directory:

```bash
uv add sqlalchemy
```

Install the PostgreSQL driver:

```bash
uv add "psycopg[binary]"
```

We also need authentication:

```bash
uv add "passlib[bcrypt]"
uv add python-jose
```

And email validation:

```bash
uv add email-validator
```

So the important dependencies are:

```text
fastapi
sqlalchemy
psycopg
passlib
python-jose
python-dotenv
email-validator
```

---

# 2.3 Backend Structure

At this point:

```text
backend/
│
├── app/
│   ├── __init__.py
│   │
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   └── auth.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── models.py
│   │
│   └── schemas/
│       ├── __init__.py
│       └── auth.py
│
├── .env
├── .gitignore
├── pyproject.toml
└── uv.lock
```

---

# 2.4 Configure `.env`

Create:

```text
backend/.env
```

Add:

```env
APP_NAME=Document Q&A API
APP_VERSION=1.0.0

DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@YOUR_HOST:5432/postgres

JWT_SECRET_KEY=CHANGE_THIS_TO_A_LONG_RANDOM_SECRET
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

GROQ_API_KEY=your_groq_api_key

PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=document-qa
```

For now, the important variable is:

```env
DATABASE_URL=...
```

### Important

Never commit `.env`:

```gitignore
.env
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.vscode/
.idea/
```

---

# 2.5 Configuration

Create:

```text
app/core/config.py
```

```python
import os

from dotenv import load_dotenv


load_dotenv()


APP_NAME = os.getenv(
    "APP_NAME",
    "Document Q&A API"
)

APP_VERSION = os.getenv(
    "APP_VERSION",
    "1.0.0"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60"
    )
)

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

PINECONE_API_KEY = os.getenv(
    "PINECONE_API_KEY"
)

PINECONE_INDEX_NAME = os.getenv(
    "PINECONE_INDEX_NAME",
    "document-qa"
)
```

---

# 2.6 Connect FastAPI to Supabase PostgreSQL

Create:

```text
app/database/connection.py
```

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL


if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not configured"
    )


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
```

Now the architecture is:

```text
FastAPI
   ↓
SQLAlchemy
   ↓
psycopg
   ↓
Supabase PostgreSQL
```

---

# 2.7 Create User Model

Create:

```text
app/database/models.py
```

```python
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Column
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
```

Our PostgreSQL table:

```text
users
┌─────────────────────────────┐
│ id                          │
│ name                        │
│ email                       │
│ password_hash               │
│ created_at                  │
└─────────────────────────────┘
```

---

# 2.8 Create the Table

There are two approaches.

For learning, we'll initially let SQLAlchemy create the table.

Update `app/main.py`:

```python
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.auth import router as auth_router

from app.core.config import (
    APP_NAME,
    APP_VERSION
)

from app.database.connection import (
    Base,
    engine
)

from app.database import models


Base.metadata.create_all(
    bind=engine
)


app = FastAPI(
    title=APP_NAME,
    description=(
        "RAG Based Document "
        "Question Answering System"
    ),
    version=APP_VERSION
)


app.include_router(
    health_router
)

app.include_router(
    auth_router
)


@app.get("/")
def root():

    return {
        "message": "Document Q&A API is running",
        "version": APP_VERSION
    }
```

The import:

```python
from app.database import models
```

is important because SQLAlchemy needs to know about the `User` model before:

```python
Base.metadata.create_all()
```

runs.

---

# 2.9 Verify Supabase Database

Go to your Supabase dashboard:

```text
Supabase
   ↓
Table Editor
```

You should eventually see:

```text
users
```

with:

```text
id
name
email
password_hash
created_at
```

---

# 2.10 Create Authentication Schemas

Create:

```text
app/schemas/auth.py
```

```python
from pydantic import BaseModel
from pydantic import EmailStr


class UserRegister(BaseModel):

    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):

    email: EmailStr
    password: str


class UserResponse(BaseModel):

    id: int
    name: str
    email: EmailStr

    model_config = {
        "from_attributes": True
    }


class TokenResponse(BaseModel):

    access_token: str
    token_type: str
```

---

# 2.11 Password Security

Create:

```text
app/core/security.py
```

```python
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(
    password: str
) -> str:

    return pwd_context.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return pwd_context.verify(
        plain_password,
        hashed_password
    )


def create_access_token(
    user_id: int
) -> str:

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

    return token
```

---

# 2.12 Create Register API

Create/update:

```text
app/api/auth.py
```

Start with:

```python
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.connection import get_db
from app.database.models import User
from app.schemas.auth import (
    UserRegister,
    UserResponse
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)
```

Then:

```python
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):

    existing_user = (
        db.query(User)
        .filter(
            User.email == user_data.email
        )
        .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(
            user_data.password
        )
    )

    db.add(new_user)

    db.commit()

    db.refresh(new_user)

    return new_user
```

---

# 2.13 Register Flow

When React eventually sends:

```json
{
    "name": "Rahul Kumar",
    "email": "rahul@gmail.com",
    "password": "Rahul@123"
}
```

the backend does:

```text
                 REGISTER
                    │
                    ▼
              FastAPI API
                    │
                    ▼
             Validate Input
                    │
                    ▼
            Check Email Exists
                    │
                    ▼
             Hash Password
                    │
                    ▼
          Supabase PostgreSQL
                    │
                    ▼
                users
```

Database:

```text
id     1
name   Rahul Kumar
email  rahul@gmail.com
password_hash   $2b$12$...
```

The actual password is **not stored**.

---

# 2.14 Login API

Add imports:

```python
from fastapi.security import OAuth2PasswordBearer
from app.core.security import (
    verify_password,
    create_access_token
)

from app.schemas.auth import (
    UserLogin,
    TokenResponse
)
```

Then:

```python
@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.email == user_data.email
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    valid_password = verify_password(
        user_data.password,
        user.password_hash
    )

    if not valid_password:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        user.id
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
```

---

# 2.15 Login Flow

```text
Email + Password
       │
       ▼
    FastAPI
       │
       ▼
 Find User in
   Supabase
       │
       ▼
 Verify Password
       │
       ▼
 Generate JWT
       │
       ▼
 Return Token
```

Response:

```json
{
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "token_type": "bearer"
}
```

---

# 2.16 JWT Authentication

Now we need to protect APIs.

Add:

```python
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from jose import jwt
```

Create:

```python
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)
```

Then:

```python
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:

        raise credentials_exception

    user = (
        db.query(User)
        .filter(
            User.id == int(user_id)
        )
        .first()
    )

    if user is None:
        raise credentials_exception

    return user
```

---

# 2.17 `/me` API

Now:

```python
@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(
        get_current_user
    )
):

    return current_user
```

This gives us:

```http
GET /api/auth/me
```

---

# 2.18 Complete `auth.py`

Your file should now look like:

```python
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import OAuth2PasswordBearer

from jose import JWTError
from jose import jwt

from sqlalchemy.orm import Session

from app.core.config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM
)

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)

from app.database.connection import get_db
from app.database.models import User

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):

    existing_user = (
        db.query(User)
        .filter(
            User.email == user_data.email
        )
        .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(
            user_data.password
        )
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse
)
def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.email == user_data.email
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    valid_password = verify_password(
        user_data.password,
        user.password_hash
    )

    if not valid_password:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        user.id
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    try:

        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:

        raise credentials_exception

    user = (
        db.query(User)
        .filter(
            User.id == int(user_id)
        )
        .first()
    )

    if user is None:
        raise credentials_exception

    return user


@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = Depends(
        get_current_user
    )
):

    return current_user
```

---

# 2.19 Important Import in `main.py`

Use:

```python
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.auth import router as auth_router

from app.core.config import (
    APP_NAME,
    APP_VERSION
)

from app.database.connection import (
    Base,
    engine
)

from app.database import models


Base.metadata.create_all(
    bind=engine
)


app = FastAPI(
    title=APP_NAME,
    description=(
        "RAG Based Document "
        "Question Answering System"
    ),
    version=APP_VERSION
)


app.include_router(
    health_router
)

app.include_router(
    auth_router
)


@app.get("/")
def root():

    return {
        "message": "Document Q&A API is running",
        "version": APP_VERSION
    }
```

---

# 2.20 Run the Backend

From:

```text
document-qa-bot/backend
```

run:

```bash
uv run fastapi dev app/main.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

You should see:

```text
Document Q&A API

Authentication
    POST /api/auth/register
    POST /api/auth/login
    GET  /api/auth/me

Health
    GET /api/health
```

---

# 2.21 Test Register

Swagger:

```text
POST /api/auth/register
```

Request:

```json
{
    "name": "Rahul Kumar",
    "email": "rahul@gmail.com",
    "password": "Rahul@123"
}
```

Response:

```json
{
    "id": 1,
    "name": "Rahul Kumar",
    "email": "rahul@gmail.com",
    "created_at": "2026-09-05T..."
}
```

---

# 2.22 Verify in Supabase

Open:

```text
Supabase Dashboard
       ↓
Table Editor
       ↓
users
```

You should see the newly created user.

```text
id | name         | email              | password_hash
---|--------------|--------------------|--------------
1  | Rahul Kumar  | rahul@gmail.com    | $2b$12$...
```

This proves:

```text
FastAPI
   ↓
SQLAlchemy
   ↓
PostgreSQL
   ↓
Supabase
```

is working.

---

# 2.23 Test Login

```http
POST /api/auth/login
```

```json
{
    "email": "rahul@gmail.com",
    "password": "Rahul@123"
}
```

Response:

```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
}
```

---

# 2.24 Test `/me`

Click:

```text
Authorize
```

Enter:

```text
Bearer YOUR_ACCESS_TOKEN
```

Then call:

```http
GET /api/auth/me
```

Response:

```json
{
    "id": 1,
    "name": "Rahul Kumar",
    "email": "rahul@gmail.com",
    "created_at": "..."
}
```

---

# Final Step 2 Architecture

We now have:

```text
                    React
                      │
                      │
                 JWT Token
                      │
                      ▼
                 ┌─────────┐
                 │ FastAPI │
                 └────┬────┘
                      │
                 SQLAlchemy
                      │
                      ▼
              ┌───────────────┐
              │    Supabase   │
              │   PostgreSQL  │
              └───────┬───────┘
                      │
                      ▼
                    users
```

And authentication:

```text
REGISTER
   │
   ├── Validate data
   ├── Check email
   ├── Hash password
   └── Save → Supabase


LOGIN
   │
   ├── Find user
   ├── Verify password
   └── Generate JWT


PROTECTED API
   │
   ├── Receive JWT
   ├── Decode JWT
   ├── Get user_id
   ├── Query Supabase
   └── Return current user
```

## One production improvement we'll make later

For a learning version, `Base.metadata.create_all()` is fine. For the production project, we'll move to **database migrations with Alembic** rather than automatically creating/changing tables when FastAPI starts.

### Next: Step 3 — Document Upload

We'll build the document system as:

```text
React
  │
  │ PDF / DOCX / TXT
  ▼
FastAPI
  │
  ▼
Authentication
  │
  ▼
Check current user
  │
  ├───────────────┐
  ▼               ▼
Local Storage    Supabase
uploads/         documents table
  │
  ▼
Document Processing
  │
  ▼
Chunking
  │
  ▼
Embeddings
  │
  ▼
Pinecone
```

For development, files go to:

```text
backend/uploads/
```

and in production the same storage service will switch to:

```text
AWS S3
```

while **Supabase PostgreSQL stores the document metadata**, and **Pinecone stores the vectors**.
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


# Step 4 — Document Processing

Now we move from **uploading a document** to **extracting and preparing its text for RAG**.

Our goal:

```text
PDF / DOCX / TXT
        ↓
   Text Extraction
        ↓
      Cleaning
        ↓
      Chunking
        ↓
   Ready for Embeddings
```

We will use **LangChain** for document loading and chunking.

---

## 4.1 Install LangChain Document Processing Packages

From `backend`:

```bash
uv add langchain
uv add langchain-community
uv add pypdf
uv add python-docx
```

We now have:

```text
FastAPI
   │
   ├── Supabase PostgreSQL
   ├── Local Storage
   │
   └── LangChain
          │
          ├── PDF Loader
          ├── DOCX Loader
          └── Text Splitter
```

---

# 4.2 Update Folder Structure

Add:

```text
backend/
│
├── app/
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── health.py
│   │   └── documents.py
│   │
│   ├── services/
│   │   ├── document_processor.py     ← NEW
│   │   │
│   │   └── storage/
│   │       └── local_storage.py
│   │
│   ├── rag/
│   │   ├── loader.py                 ← NEW
│   │   └── splitter.py               ← NEW
│   │
│   └── ...
│
└── uploads/
```

We'll keep **document processing separate from the API route**.

---

# 4.3 Create Document Loader

Create:

```text
app/rag/loader.py
```

```python
from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)


def load_document(file_path: str):

    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":

        loader = PyPDFLoader(file_path)

    elif extension == ".docx":

        loader = Docx2txtLoader(file_path)

    elif extension == ".txt":

        loader = TextLoader(
            file_path,
            encoding="utf-8"
        )

    else:

        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    return loader.load()
```

---

# 4.4 What Does `loader.load()` Return?

Suppose we upload:

```text
python.pdf
```

with 10 pages.

LangChain returns something conceptually like:

```python
[
    Document(
        page_content="Python is a programming language...",
        metadata={
            "source": "uploads/abc.pdf",
            "page": 0
        }
    ),

    Document(
        page_content="Python supports object-oriented...",
        metadata={
            "source": "uploads/abc.pdf",
            "page": 1
        }
    ),

    ...
]
```

So:

```text
PDF
 ↓
Page 1 → Document
Page 2 → Document
Page 3 → Document
...
```

The metadata is very useful later.

For example, our RAG answer can eventually show:

```text
Source: python.pdf
Page: 5
```

---

# 4.5 Create Text Splitter

Create:

```text
app/rag/splitter.py
```

```python
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
)


def split_documents(documents):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )

    chunks = splitter.split_documents(
        documents
    )

    return chunks
```

We need the splitter package:

```bash
uv add langchain-text-splitters
```

---

# 4.6 Why Chunking?

Imagine a PDF contains:

```text
100 pages
```

We don't want to send the entire PDF to the LLM every time.

Instead:

```text
100-page PDF
      ↓
Extract text
      ↓
Split into chunks
      ↓
Chunk 1
Chunk 2
Chunk 3
...
Chunk 500
```

Later Pinecone will search these chunks.

For example:

```text
Question:

"What is supervised learning?"

              ↓

           Pinecone

              ↓

       Relevant chunks

              ↓

Chunk 145
Chunk 302
Chunk 411

              ↓

            Groq

              ↓

           Answer
```

---

# 4.7 Understanding `chunk_size`

We currently use:

```python
chunk_size=1000
```

Conceptually:

```text
Chunk 1
────────────────────
~1000 characters
────────────────────

Chunk 2
────────────────────
~1000 characters
────────────────────
```

But we also use:

```python
chunk_overlap=200
```

So:

```text
Chunk 1
████████████████████

            █████
            overlap

                ████████████████████
                Chunk 2
```

Why overlap?

To avoid losing context between chunks.

For example:

```text
Chunk 1:
"Machine learning models learn patterns from data..."

Chunk 2:
"...patterns from data are then used to make predictions."
```

The overlap preserves some context.

---

# 4.8 Create Document Processor

Create:

```text
app/services/document_processor.py
```

```python
from app.rag.loader import load_document
from app.rag.splitter import split_documents


def process_document(
    file_path: str
):

    documents = load_document(
        file_path
    )

    chunks = split_documents(
        documents
    )

    return chunks
```

Our processing pipeline is now:

```text
File
 ↓
load_document()
 ↓
LangChain Documents
 ↓
split_documents()
 ↓
Chunks
```

---

# 4.9 Test the Processor

Before connecting this to FastAPI, let's test it separately.

Create:

```text
test_processing.py
```

in the backend directory:

```python
from app.services.document_processor import (
    process_document
)


file_path = "uploads/example.pdf"


chunks = process_document(
    file_path
)

print(
    f"Total chunks: {len(chunks)}"
)

for index, chunk in enumerate(
    chunks[:5]
):

    print("\n----------------")
    print(f"Chunk: {index + 1}")
    print("----------------")

    print(
        chunk.page_content[:500]
    )

    print(
        "Metadata:",
        chunk.metadata
    )
```

Run:

```bash
uv run python test_processing.py
```

Expected:

```text
Total chunks: 35

----------------
Chunk: 1
----------------

Python is a high-level programming
language...

Metadata:
{
    'source': 'uploads/example.pdf',
    'page': 0
}
```

---

# 4.10 Connect Processing to Upload

Currently our upload API does:

```text
Upload
 ↓
Save file
 ↓
Save database record
```

We want:

```text
Upload
 ↓
Save file
 ↓
Save DB record
 ↓
Process document
 ↓
Extract text
 ↓
Create chunks
 ↓
Update status
```

---

# 4.11 Update Document Status

When a file is first uploaded:

```text
uploaded
```

Then:

```text
processing
```

Then:

```text
processed
```

Later:

```text
embedded
```

So the lifecycle becomes:

```text
uploaded
    ↓
processing
    ↓
processed
    ↓
embedded
```

This is important in a real application because document processing can take time.

---

# 4.12 Update Upload API

In:

```text
app/api/documents.py
```

add:

```python
from app.services.document_processor import (
    process_document
)
```

Then after creating the database record:

```python
document.status = "processing"

db.commit()
```

Process:

```python
try:

    chunks = process_document(
        file_path
    )

    document.status = "processed"

    db.commit()

except Exception as e:

    document.status = "failed"

    db.commit()

    raise HTTPException(
        status_code=500,
        detail=(
            f"Document processing failed: {str(e)}"
        )
    )
```

---

# 4.13 Complete Processing Flow

Now:

```text
                    Upload
                       │
                       ▼
                   FastAPI
                       │
                       ▼
                JWT Validation
                       │
                       ▼
                Save Local File
                       │
                       ▼
                Supabase Record
                       │
                       ▼
                   processing
                       │
                       ▼
                  LangChain
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
             PDF      DOCX      TXT
              │        │        │
              └────────┼────────┘
                       ▼
                Extract Text
                       │
                       ▼
                   Chunking
                       │
                       ▼
                   processed
```

---

# 4.14 Important: We Are NOT Sending Chunks to Pinecone Yet

At this point:

```text
Document
   ↓
Text
   ↓
Chunks
```

We stop here.

Next we need:

```text
Chunks
   ↓
Embedding Model
   ↓
Vectors
   ↓
Pinecone
```

This separation is important for teaching.

---

# 4.15 Store Processing Information

Our current `documents` table has:

```text
id
user_id
filename
file_path
file_type
file_size
status
created_at
```

Eventually we'll add:

```text
chunk_count
processing_error
storage_key
```

For example:

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
chunk_count
processing_error
created_at
```

Example:

```text
id                 1
user_id            7
filename           python.pdf
file_type          .pdf
file_size          245678
status             processed
chunk_count        43
processing_error   NULL
```

We'll add those fields properly when we introduce migrations.

---

# 4.16 The RAG Pipeline Is Taking Shape

We now have the first half:

```text
             DOCUMENT INGESTION
                    │
                    ▼
              Upload File
                    │
                    ▼
             Local Storage
                    │
                    ▼
             Text Extraction
                    │
                    ▼
                Chunking
                    │
                    ▼
              ┌───────────┐
              │   NEXT    │
              │           │
              │ Embedding │
              └─────┬─────┘
                    │
                    ▼
                 Pinecone
```

And eventually the query side will be:

```text
             USER QUESTION
                    │
                    ▼
               FastAPI
                    │
                    ▼
             Create Embedding
                    │
                    ▼
               Pinecone
                    │
                    ▼
             Relevant Chunks
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

# Step 4 Complete ✅

We now have:

```text
✅ Supabase PostgreSQL
✅ User Authentication
✅ JWT
✅ Document Upload
✅ Local Development Storage
✅ PDF Loader
✅ DOCX Loader
✅ TXT Loader
✅ Text Extraction
✅ Recursive Chunking
✅ Processing Status
```

### Next — Step 5: Embeddings + Pinecone

This is where the project becomes a real **vector-based RAG system**:

```text
Document
   ↓
Chunks
   ↓
Embedding Model
   ↓
Vector
   ↓
Pinecone
```

We'll create a Pinecone index, generate embeddings, store each chunk with metadata such as:

```json
{
  "user_id": 1,
  "document_id": 5,
  "filename": "python.pdf",
  "page": 10,
  "text": "..."
}
```

and implement **user-specific vector filtering**, so one student can never retrieve another student's document chunks.
# Step 6 — Semantic Search 🔎

Now that our document chunks are stored in **Pinecone**, we need to retrieve the most relevant chunks when a user asks a question.

Our pipeline becomes:

```text
User Question
      ↓
Question Embedding
      ↓
Pinecone Similarity Search
      ↓
Top Relevant Chunks
      ↓
Filter by user_id
      ↓
Retrieved Context
```

This is the **Retrieval** part of RAG.

---

## 6.1 Real-world problem

Suppose a student uploaded:

```text
python.pdf
machine_learning.pdf
fastapi.pdf
```

Then asks:

> What is dependency injection in FastAPI?

We don't want to send all three PDFs to Groq.

Instead:

```text
Question
   ↓
"What is dependency injection in FastAPI?"
   ↓
Embedding
   ↓
Pinecone
   ↓
Find similar chunks
   ↓
Top 5 chunks
```

For example:

```text
Chunk 1 → FastAPI dependency injection
Chunk 2 → Depends()
Chunk 3 → Dependency functions
Chunk 4 → Request dependencies
Chunk 5 → Authentication dependencies
```

These chunks will become the **context** for the LLM in the next step.

---

# 6.2 Add search function

Open:

```text
app/rag/vector_store.py
```

Add:

```python
def search_chunks(
    query: str,
    user_id: int,
    top_k: int = 5
):
    index = get_index()

    # Convert question into vector
    query_vector = embedding_model.embed_query(query)

    # Search Pinecone
    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        filter={
            "user_id": str(user_id)
        }
    )

    return results
```

The important part is:

```python
filter={
    "user_id": str(user_id)
}
```

This ensures that users retrieve **only their own documents**.

---

# 6.3 Create search schema

Create:

```text
app/schemas/search.py
```

```python
from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    text: str
    score: float
    document_id: str
    filename: str | None = None
    page: int | None = None
```

---

# 6.4 Create search API

Create:

```text
app/api/search.py
```

```python
from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.database.models import User
from app.rag.vector_store import search_chunks
from app.schemas.search import (
    SearchRequest,
    SearchResult
)


router = APIRouter(
    prefix="/api/search",
    tags=["Search"]
)


@router.post(
    "",
    response_model=list[SearchResult]
)
def semantic_search(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_user)
):

    results = search_chunks(
        query=search_request.query,
        user_id=current_user.id,
        top_k=search_request.top_k
    )

    search_results = []

    for match in results["matches"]:

        metadata = match.get("metadata", {})

        search_results.append(
            SearchResult(
                text=metadata.get("text", ""),
                score=match.get("score", 0),
                document_id=metadata.get(
                    "document_id",
                    ""
                ),
                filename=metadata.get(
                    "filename"
                ),
                page=metadata.get(
                    "page"
                )
            )
        )

    return search_results
```

---

# 6.5 Add search router to FastAPI

Open:

```text
app/main.py
```

Add:

```python
from app.api.search import router as search_router
```

Then:

```python
app.include_router(search_router)
```

Your `main.py` should now contain:

```python
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.search import router as search_router

from app.core.config import APP_NAME, APP_VERSION

from app.database.connection import Base, engine
from app.database import models


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=APP_NAME,
    description="RAG Based Document Question Answering System",
    version=APP_VERSION
)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)


@app.get("/")
def root():
    return {
        "message": "Document Q&A API is running",
        "version": APP_VERSION
    }
```

---

# 6.6 Important correction: store filename in Pinecone metadata

Our current `store_chunks()` metadata contains:

```python
metadata = {
    "user_id": str(user_id),
    "document_id": str(document_id),
    "text": text,
    "source": chunk.metadata.get("source", ""),
    "page": chunk.metadata.get("page", 0)
}
```

We should also store the original filename.

Modify the function.

### `app/rag/vector_store.py`

```python
def store_chunks(
    chunks,
    user_id: int,
    document_id: int,
    filename: str
):

    index = get_index()

    vectors = []

    for chunk in chunks:

        text = chunk.page_content

        vector = embedding_model.embed_query(
            text
        )

        metadata = {
            "user_id": str(user_id),
            "document_id": str(document_id),
            "filename": filename,
            "text": text,
            "source": chunk.metadata.get(
                "source",
                ""
            ),
            "page": chunk.metadata.get(
                "page",
                0
            )
        }

        vectors.append(
            {
                "id": str(uuid4()),
                "values": vector,
                "metadata": metadata
            }
        )

    index.upsert(
        vectors=vectors
    )

    return len(vectors)
```

Then in `documents.py`:

```python
vector_count = store_chunks(
    chunks=chunks,
    user_id=current_user.id,
    document_id=document.id,
    filename=document.filename
)
```

---

# 6.7 Test semantic search

Start FastAPI:

```bash
uv run fastapi dev app/main.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

You should see:

```text
Authentication
Documents
Search
Health
```

First:

```text
POST /api/auth/register
```

Then:

```text
POST /api/auth/login
```

Copy the JWT token.

Click:

```text
Authorize
```

Enter:

```text
Bearer YOUR_ACCESS_TOKEN
```

---

## 6.8 Test `/api/search`

Request:

```json
{
    "query": "What is FastAPI?",
    "top_k": 5
}
```

Possible response:

```json
[
    {
        "text": "FastAPI is a modern Python framework...",
        "score": 0.91,
        "document_id": "5",
        "filename": "python.pdf",
        "page": 12
    },
    {
        "text": "FastAPI provides dependency injection...",
        "score": 0.87,
        "document_id": "5",
        "filename": "python.pdf",
        "page": 15
    }
]
```

The `score` represents how similar the stored chunk is to the user's question.

---

# 6.9 Understand similarity search

Traditional keyword search:

```text
Question:
"What is FastAPI?"
```

looks for words such as:

```text
FastAPI
```

Semantic search instead understands meaning.

For example:

```text
Question:
"What does FastAPI do?"
```

could retrieve:

```text
"FastAPI is a Python framework for building APIs."
```

even though the exact words aren't identical.

That's the power of **embeddings + vector search**.

---

# 6.10 Our RAG architecture so far

We have now completed:

```text
                    USER
                     │
                     ▼
              ┌─────────────┐
              │   FastAPI   │
              └──────┬──────┘
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
      Upload                  Search
          │                     │
          ▼                     ▼
   Local Storage          Create Embedding
          │                     │
          ▼                     ▼
    Text Extraction         Pinecone
          │                     │
          ▼                     ▼
       Chunking             Similarity
          │                   Search
          ▼                     │
     Embeddings                │
          │                     │
          ▼                     ▼
       Pinecone          Relevant Chunks
                                │
                                ▼
                         ┌─────────────┐
                         │  Next: Groq │
                         └─────────────┘
```

---

# Step 6 is conceptually very important

Students should understand:

### Supabase

Stores:

```text
users
documents
```

### Local Storage

Stores:

```text
actual PDF/DOCX/TXT files
```

### Pinecone

Stores:

```text
chunk
   +
embedding
   +
metadata
```

### FastAPI

Connects everything.

---

# Next — Step 7: Groq + LangChain

Now we finally introduce the **LLM**.

The flow will become:

```text
User Question
      ↓
Pinecone Search
      ↓
Top 5 Relevant Chunks
      ↓
Context
      ↓
LangChain Prompt
      ↓
Groq LLM
      ↓
Final Answer
```

Example:

```text
User:
"What is FastAPI?"
```

Pinecone retrieves:

```text
Chunk 1
Chunk 2
Chunk 3
```

Then LangChain creates:

```text
Context:
FastAPI is a Python framework...

Question:
What is FastAPI?
```

Groq generates:

```text
FastAPI is a modern Python web framework
used for building APIs...
```

After that, we'll introduce **LangGraph** and turn these individual steps into a proper production RAG workflow.


Yes. For this project, I recommend **not** hard-coding Groq into the chat API.

Instead, create a **provider abstraction layer**:

```text
                    FastAPI
                       │
                       ▼
                 /api/chat
                       │
                       ▼
                LLM Factory
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
      Groq           OpenAI         Gemini
        │              │              │
   ChatGroq        ChatOpenAI   ChatGoogleGenerativeAI
                       │
                    Claude
                       │
                 ChatAnthropic
```

This is a better production architecture because LangChain has provider-specific integrations for OpenAI, Groq, Gemini and Anthropic. ([Docs by LangChain][1])

Then later you can add:

```text
Mistral
DeepSeek
Qwen
OpenRouter
AWS Bedrock
Azure OpenAI
Ollama
...
```

without changing your `/api/chat` endpoint.

# Step 7 — Multi-Provider AI API

## 7.1 Install provider packages

From `backend/`:

```bash
uv add langchain-openai
uv add langchain-groq
uv add langchain-google-genai
uv add langchain-anthropic
```

These are the current LangChain provider integrations. ([Docs by LangChain][1])

---

# 7.2 Update `.env`

```env
# =========================
# AI PROVIDERS
# =========================

# Groq
GROQ_API_KEY=your_groq_api_key

# OpenAI / ChatGPT
OPENAI_API_KEY=your_openai_api_key

# Google Gemini
GOOGLE_API_KEY=your_google_api_key

# Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_api_key


# =========================
# DEFAULT AI
# =========================

DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=qwen/qwen3-32b
```

You don't need to fill every key immediately.

For example, if you're currently using Groq:

```env
GROQ_API_KEY=xxxxxxxx
```

and leave the others empty.

---

# 7.3 Update `config.py`

Open:

```text
app/core/config.py
```

Add:

```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

DEFAULT_LLM_PROVIDER = os.getenv(
    "DEFAULT_LLM_PROVIDER",
    "groq"
)

DEFAULT_LLM_MODEL = os.getenv(
    "DEFAULT_LLM_MODEL",
    "qwen/qwen3-32b"
)
```

So your configuration now knows about multiple providers.

---

# 7.4 Create LLM folder

We already have:

```text
app/
├── rag/
└── graph/
```

Add:

```text
app/
└── llm/
    ├── __init__.py
    ├── factory.py
    └── providers.py
```

This separation is important.

```text
llm/
    │
    ├── factory.py       → decides which provider to use
    │
    └── providers.py     → provider implementations
```

---

# 7.5 Create provider registry

### `app/llm/providers.py`

```python
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

from app.core.config import (
    GROQ_API_KEY,
    OPENAI_API_KEY,
    GOOGLE_API_KEY,
    ANTHROPIC_API_KEY,
)


def create_groq(model: str, temperature: float):
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not configured"
        )

    return ChatGroq(
        model=model,
        api_key=GROQ_API_KEY,
        temperature=temperature,
    )


def create_openai(model: str, temperature: float):
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not configured"
        )

    return ChatOpenAI(
        model=model,
        api_key=OPENAI_API_KEY,
        temperature=temperature,
    )


def create_gemini(model: str, temperature: float):
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY is not configured"
        )

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=GOOGLE_API_KEY,
        temperature=temperature,
    )


def create_anthropic(model: str, temperature: float):
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY is not configured"
        )

    return ChatAnthropic(
        model=model,
        api_key=ANTHROPIC_API_KEY,
        temperature=temperature,
    )
```

---

# 7.6 Create LLM Factory

Now create:

### `app/llm/factory.py`

```python
from app.core.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
)

from app.llm.providers import (
    create_groq,
    create_openai,
    create_gemini,
    create_anthropic,
)


PROVIDERS = {
    "groq": create_groq,
    "openai": create_openai,
    "gemini": create_gemini,
    "anthropic": create_anthropic,
}


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
):

    provider = (
        provider or DEFAULT_LLM_PROVIDER
    ).lower()

    model = (
        model or DEFAULT_LLM_MODEL
    )

    if provider not in PROVIDERS:

        available = ", ".join(
            PROVIDERS.keys()
        )

        raise ValueError(
            f"Unsupported LLM provider: "
            f"{provider}. "
            f"Available providers: {available}"
        )

    llm_creator = PROVIDERS[provider]

    return llm_creator(
        model=model,
        temperature=temperature
    )
```

Now the application doesn't care which LLM is being used.

---

# 7.7 Why use a factory?

Without a factory, your code might become:

```python
if provider == "groq":
    ...

elif provider == "openai":
    ...

elif provider == "gemini":
    ...

elif provider == "anthropic":
    ...
```

inside every API.

That becomes difficult to maintain.

Instead:

```python
llm = get_llm(
    provider="groq",
    model="qwen/qwen3-32b"
)
```

or:

```python
llm = get_llm(
    provider="openai",
    model="gpt-5.4-mini"
)
```

or:

```python
llm = get_llm(
    provider="gemini",
    model="gemini-2.5-flash"
)
```

or:

```python
llm = get_llm(
    provider="anthropic",
    model="claude-sonnet-4-5"
)
```

The rest of your RAG code remains unchanged.

---

# 7.8 Create Chat Schema

Create:

```text
app/schemas/chat.py
```

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1
    )

    provider: str | None = None

    model: str | None = None

    temperature: float = Field(
        default=0.2,
        ge=0,
        le=2
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20
    )


class ChatResponse(BaseModel):

    answer: str

    provider: str

    model: str

    sources: list
```

---

# 7.9 Create Chat API

Create:

```text
app/api/chat.py
```

```python
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.database.models import User

from app.llm.factory import get_llm

from app.rag.vector_store import search_chunks

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)


@router.post(
    "",
    response_model=ChatResponse
)
def chat(
    request: ChatRequest,
    current_user: User = Depends(
        get_current_user
    )
):

    # =========================
    # 1. Retrieve documents
    # =========================

    results = search_chunks(
        query=request.question,
        user_id=current_user.id,
        top_k=request.top_k
    )

    matches = results.get(
        "matches",
        []
    )

    if not matches:

        raise HTTPException(
            status_code=404,
            detail=(
                "No relevant information "
                "was found in your documents."
            )
        )

    # =========================
    # 2. Build context
    # =========================

    context_parts = []

    sources = []

    for match in matches:

        metadata = match.get(
            "metadata",
            {}
        )

        text = metadata.get(
            "text",
            ""
        )

        context_parts.append(text)

        sources.append({
            "document_id": metadata.get(
                "document_id"
            ),
            "filename": metadata.get(
                "filename"
            ),
            "page": metadata.get(
                "page"
            ),
            "score": match.get(
                "score"
            )
        })

    context = "\n\n".join(
        context_parts
    )

    # =========================
    # 3. Get LLM
    # =========================

    provider = (
        request.provider
        or "groq"
    )

    model = request.model

    try:

        llm = get_llm(
            provider=provider,
            model=model,
            temperature=request.temperature
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    # =========================
    # 4. Create RAG prompt
    # =========================

    prompt = f"""
You are a helpful document question-answering assistant.

Answer the user's question using ONLY
the provided context.

If the answer is not present in the context,
say:

"I could not find the answer in your documents."

Do not make up information.

Context:
----------------
{context}
----------------

Question:
{request.question}

Answer:
"""

    # =========================
    # 5. Call LLM
    # =========================

    response = llm.invoke(prompt)

    answer = response.content

    # =========================
    # 6. Return response
    # =========================

    return ChatResponse(
        answer=answer,
        provider=provider,
        model=model or "default",
        sources=sources
    )
```

---

# 7.10 Register Chat Router

Open:

```text
app/main.py
```

Add:

```python
from app.api.chat import router as chat_router
```

Then:

```python
app.include_router(chat_router)
```

Your routers are now:

```python
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(chat_router)
```

---

# 7.11 Test Groq

Start:

```bash
uv run fastapi dev app/main.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

Authorize with your JWT.

Call:

```http
POST /api/chat
```

Request:

```json
{
    "question": "What is FastAPI?",
    "provider": "groq",
    "model": "qwen/qwen3-32b",
    "temperature": 0.2,
    "top_k": 5
}
```

Response:

```json
{
    "answer": "FastAPI is a modern Python framework...",
    "provider": "groq",
    "model": "qwen/qwen3-32b",
    "sources": [
        {
            "document_id": "5",
            "filename": "python.pdf",
            "page": 12,
            "score": 0.91
        }
    ]
}
```

Groq's current LangChain integration is `ChatGroq` from `langchain-groq`. ([Docs by LangChain][2])

---

# 7.12 Switch to OpenAI

Same API:

```json
{
    "question": "Explain FastAPI dependency injection",
    "provider": "openai",
    "model": "gpt-5.4-mini",
    "temperature": 0.2,
    "top_k": 5
}
```

No changes to:

```text
Pinecone
Supabase
document processing
embedding
retrieval
FastAPI endpoint
```

Only the LLM changes.

LangChain's official OpenAI integration uses `ChatOpenAI`. ([Docs by LangChain][1])

---

# 7.13 Switch to Gemini

```json
{
    "question": "Explain FastAPI dependency injection",
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "temperature": 0.2,
    "top_k": 5
}
```

Gemini is provided through LangChain's `ChatGoogleGenerativeAI` integration. ([Docs by LangChain][3])

---

# 7.14 Switch to Claude

```json
{
    "question": "Explain FastAPI dependency injection",
    "provider": "anthropic",
    "model": "claude-sonnet-4-5",
    "temperature": 0.2,
    "top_k": 5
}
```

Claude is accessed through LangChain's `ChatAnthropic` integration. ([Docs by LangChain][4])

---

# 7.15 The important architecture

Your application is now:

```text
                         React
                           │
                           ▼
                       FastAPI
                           │
                    ┌──────┴──────┐
                    │             │
                    ▼             ▼
                 Auth          Chat API
                    │             │
                    ▼             ▼
                Supabase       Retriever
                                  │
                                  ▼
                               Pinecone
                                  │
                                  ▼
                           Relevant Chunks
                                  │
                                  ▼
                            LLM Factory
                                  │
             ┌────────────────────┼───────────────────┐
             │                    │                   │
             ▼                    ▼                   ▼
           Groq                OpenAI              Gemini
       ChatGroq             ChatOpenAI       ChatGoogleGenerativeAI
             │                    │                   │
             └────────────────────┼───────────────────┘
                                  │
                                  ▼
                              Answer
                                  │
                                  ▼
                                React
```

## Why this is better

Later, adding another provider is simple:

```text
app/llm/providers.py
```

Add:

```python
def create_new_provider(
    model: str,
    temperature: float
):
    ...
```

Then:

```python
PROVIDERS = {
    "groq": create_groq,
    "openai": create_openai,
    "gemini": create_gemini,
    "anthropic": create_anthropic,
    "new_provider": create_new_provider,
}
```

**The Chat API does not change.**

---

# One more improvement before LangGraph

I recommend **not putting all of the RAG logic inside `app/api/chat.py` permanently**.

Right now:

```text
chat.py
 ├── retrieval
 ├── context creation
 ├── prompt
 ├── LLM selection
 └── LLM invocation
```

That's okay for learning Step 7, but our production architecture should become:

```text
app/
│
├── api/
│   └── chat.py
│
├── llm/
│   ├── factory.py
│   └── providers.py
│
├── rag/
│   ├── loader.py
│   ├── splitter.py
│   ├── embeddings.py
│   ├── vector_store.py
│   └── retriever.py
│
└── graph/
    ├── state.py
    ├── nodes.py
    └── workflow.py
```

Then the final architecture will be:

```text
React
  ↓
FastAPI
  ↓
Chat API
  ↓
LangGraph
  │
  ├── Retrieve
  │      ↓
  │   Pinecone
  │
  ├── Build Context
  │
  ├── Select LLM
  │      ↓
  │   LLM Factory
  │      ├── Groq
  │      ├── OpenAI
  │      ├── Gemini
  │      ├── Claude
  │      └── Future Providers
  │
  └── Generate Answer
          ↓
       Response
```

**Next step should therefore be Step 8: LangGraph RAG workflow** — we'll move retrieval, context creation, LLM generation, and state management into proper LangGraph nodes instead of keeping the logic inside the API route.

[1]: https://docs.langchain.com/oss/python/integrations/chat/openai?utm_source=chatgpt.com "ChatOpenAI integration - Docs by LangChain"
[2]: https://docs.langchain.com/oss/python/integrations/chat/groq?utm_source=chatgpt.com "ChatGroq integration - Docs by LangChain"
[3]: https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai?utm_source=chatgpt.com "ChatGoogleGenerativeAI integration - Docs by LangChain"
[4]: https://docs.langchain.com/oss/python/integrations/chat/anthropic?utm_source=chatgpt.com "ChatAnthropic integration - Docs by LangChain"




# Step 8 — LangGraph RAG Workflow

Now we'll convert our current RAG logic into a **LangGraph workflow**.

Instead of:

```text
FastAPI
   ↓
Search
   ↓
Prompt
   ↓
LLM
```

we'll build:

```text
FastAPI
   ↓
LangGraph
   │
   ├── Retrieve
   │
   ├── Build Context
   │
   ├── Generate Answer
   │
   └── Return Response
```

This gives us a proper foundation for adding things later like:

* query rewriting
* document relevance checking
* web search fallback
* multiple LLM providers
* conversation memory
* answer validation
* retry/fallback
* streaming

---

## 8.1 Install LangGraph

From `backend/`:

```bash
uv add langgraph
```

We already have LangChain installed.

---

# 8.2 Create the graph structure

Change:

```text
app/
└── graph/
    └── __init__.py
```

to:

```text
app/
└── graph/
    ├── __init__.py
    ├── state.py
    ├── nodes.py
    └── workflow.py
```

---

# 8.3 Create Graph State

Create:

### `app/graph/state.py`

```python
from typing import TypedDict


class RAGState(TypedDict, total=False):

    # User information
    user_id: int

    # User question
    question: str

    # Retrieval configuration
    top_k: int

    # LLM configuration
    provider: str
    model: str | None
    temperature: float

    # Retrieved Pinecone results
    retrieved_chunks: list

    # Combined context
    context: str

    # Final answer
    answer: str

    # Source information
    sources: list
```

Think of `RAGState` as a **shared notebook** between LangGraph nodes.

For example:

```text
State
│
├── question
├── user_id
├── retrieved_chunks
├── context
├── answer
└── sources
```

Each node reads some information and adds/updates information.

---

# 8.4 Create Retrieval Node

Create:

### `app/graph/nodes.py`

```python
from app.rag.vector_store import search_chunks
from app.llm.factory import get_llm


def retrieve_node(state):

    question = state["question"]
    user_id = state["user_id"]
    top_k = state.get("top_k", 5)

    results = search_chunks(
        query=question,
        user_id=user_id,
        top_k=top_k
    )

    matches = results.get(
        "matches",
        []
    )

    retrieved_chunks = []
    sources = []

    for match in matches:

        metadata = match.get(
            "metadata",
            {}
        )

        retrieved_chunks.append({
            "text": metadata.get(
                "text",
                ""
            ),
            "score": match.get(
                "score",
                0
            ),
            "document_id": metadata.get(
                "document_id"
            ),
            "filename": metadata.get(
                "filename"
            ),
            "page": metadata.get(
                "page"
            )
        })

        sources.append({
            "document_id": metadata.get(
                "document_id"
            ),
            "filename": metadata.get(
                "filename"
            ),
            "page": metadata.get(
                "page"
            ),
            "score": match.get(
                "score",
                0
            )
        })

    return {
        "retrieved_chunks": retrieved_chunks,
        "sources": sources
    }
```

---

# 8.5 Create Context Node

Add to the same file:

```python
def build_context_node(state):

    retrieved_chunks = state.get(
        "retrieved_chunks",
        []
    )

    context_parts = []

    for index, chunk in enumerate(
        retrieved_chunks,
        start=1
    ):

        text = chunk.get(
            "text",
            ""
        )

        context_parts.append(
            f"[Context {index}]\n{text}"
        )

    context = "\n\n".join(
        context_parts
    )

    return {
        "context": context
    }
```

Now:

```text
Pinecone
   ↓
5 chunks
   ↓
Context Node
   ↓
one context string
```

---

# 8.6 Create LLM Generation Node

Add:

```python
def generate_answer_node(state):

    question = state["question"]

    context = state.get(
        "context",
        ""
    )

    provider = state.get(
        "provider",
        "groq"
    )

    model = state.get(
        "model"
    )

    temperature = state.get(
        "temperature",
        0.2
    )

    llm = get_llm(
        provider=provider,
        model=model,
        temperature=temperature
    )

    prompt = f"""
You are a helpful document question-answering assistant.

Your job is to answer the user's question
using ONLY the supplied document context.

Rules:

1. Do not invent information.
2. Do not use outside knowledge.
3. If the answer is not present in the context,
   clearly say that you could not find the answer
   in the uploaded documents.
4. Give a clear and concise answer.

Document Context:
========================

{context}

========================

User Question:
{question}

Answer:
"""

    response = llm.invoke(prompt)

    return {
        "answer": response.content
    }
```

---

# 8.7 Our nodes

We now have three nodes:

```text
retrieve_node
      ↓
build_context_node
      ↓
generate_answer_node
```

Conceptually:

```text
             Question
                 │
                 ▼
        ┌─────────────────┐
        │    Retrieve     │
        │    Pinecone     │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Build Context   │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Generate Answer │
        │   Groq/OpenAI   │
        │ Gemini/Claude   │
        └────────┬────────┘
                 │
                 ▼
               Answer
```

---

# 8.8 Create LangGraph Workflow

Create:

### `app/graph/workflow.py`

```python
from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from app.graph.state import RAGState

from app.graph.nodes import (
    retrieve_node,
    build_context_node,
    generate_answer_node,
)


def create_rag_graph():

    graph = StateGraph(RAGState)

    # Add nodes
    graph.add_node(
        "retrieve",
        retrieve_node
    )

    graph.add_node(
        "build_context",
        build_context_node
    )

    graph.add_node(
        "generate_answer",
        generate_answer_node
    )

    # Define workflow
    graph.add_edge(
        START,
        "retrieve"
    )

    graph.add_edge(
        "retrieve",
        "build_context"
    )

    graph.add_edge(
        "build_context",
        "generate_answer"
    )

    graph.add_edge(
        "generate_answer",
        END
    )

    return graph.compile()
```

---

# 8.9 Understand `StateGraph`

This:

```python
graph = StateGraph(RAGState)
```

means:

> Create a workflow whose shared state follows `RAGState`.

Then:

```python
graph.add_node(
    "retrieve",
    retrieve_node
)
```

means:

```text
Node Name       Function

retrieve   →    retrieve_node()
```

Then:

```python
graph.add_edge(
    START,
    "retrieve"
)
```

means:

```text
START → retrieve
```

And:

```python
graph.add_edge(
    "retrieve",
    "build_context"
)
```

means:

```text
retrieve → build_context
```

Finally:

```python
graph.add_edge(
    "generate_answer",
    END
)
```

means:

```text
generate_answer → END
```

---

# 8.10 Test the LangGraph independently

Create:

```text
backend/
└── test_graph.py
```

```python
from app.graph.workflow import create_rag_graph


graph = create_rag_graph()


result = graph.invoke({

    "user_id": 1,

    "question": "What is FastAPI?",

    "top_k": 5,

    "provider": "groq",

    "model": "qwen/qwen3-32b",

    "temperature": 0.2

})


print("\n====================")
print("ANSWER")
print("====================")

print(result["answer"])


print("\n====================")
print("SOURCES")
print("====================")

for source in result["sources"]:
    print(source)
```

Run:

```bash
uv run python test_graph.py
```

Expected:

```text
====================
ANSWER
====================

FastAPI is a modern Python web framework
used for building APIs...

====================
SOURCES
====================

{'document_id': '5',
 'filename': 'python.pdf',
 'page': 12,
 'score': 0.91}
```

---

# 8.11 Now simplify `chat.py`

This is where LangGraph becomes useful.

Our old `chat.py` contained:

```text
Retrieval
Context creation
LLM selection
Prompt
LLM invocation
Response
```

We can now make the API much cleaner.

Replace the main logic with:

### `app/api/chat.py`

```python
from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import get_current_user
from app.database.models import User

from app.graph.workflow import create_rag_graph

from app.schemas.chat import (
    ChatRequest,
    ChatResponse
)


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)


rag_graph = create_rag_graph()


@router.post(
    "",
    response_model=ChatResponse
)
def chat(
    request: ChatRequest,
    current_user: User = Depends(
        get_current_user
    )
):

    try:

        result = rag_graph.invoke({

            "user_id": current_user.id,

            "question": request.question,

            "top_k": request.top_k,

            "provider": request.provider or "groq",

            "model": request.model,

            "temperature": request.temperature

        })

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"RAG processing failed: {str(e)}"
        )

    if not result.get("answer"):

        raise HTTPException(
            status_code=500,
            detail="Could not generate an answer"
        )

    return ChatResponse(

        answer=result["answer"],

        provider=request.provider or "groq",

        model=request.model or "default",

        sources=result.get(
            "sources",
            []
        )
    )
```

Now the API is responsible only for:

```text
HTTP request
     ↓
Authentication
     ↓
LangGraph
     ↓
HTTP response
```

That's much cleaner.

---

# 8.12 Our complete backend architecture

We now have:

```text
document-qa-bot/
│
└── backend/
    │
    ├── app/
    │
    ├── api/
    │   ├── auth.py
    │   ├── documents.py
    │   ├── search.py
    │   └── chat.py
    │
    ├── core/
    │   ├── config.py
    │   └── security.py
    │
    ├── database/
    │   ├── connection.py
    │   └── models.py
    │
    ├── schemas/
    │   ├── auth.py
    │   ├── document.py
    │   ├── search.py
    │   └── chat.py
    │
    ├── services/
    │   ├── document_processor.py
    │   └── storage/
    │       └── local_storage.py
    │
    ├── rag/
    │   ├── loader.py
    │   ├── splitter.py
    │   ├── embeddings.py
    │   └── vector_store.py
    │
    ├── llm/
    │   ├── factory.py
    │   └── providers.py
    │
    └── graph/
        ├── state.py
        ├── nodes.py
        └── workflow.py
```

---

# 8.13 The complete RAG flow

We have now built:

```text
                    React
                      │
                      ▼
                   FastAPI
                      │
              ┌───────┴────────┐
              │                │
              ▼                ▼
          Register           Login
              │                │
              └───────┬────────┘
                      ▼
                     JWT
                      │
                      ▼
                Upload Document
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
    Local Storage             Supabase
          │                    PostgreSQL
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
```

Then when the user asks:

```text
"What is FastAPI?"
```

we have:

```text
                     Question
                         │
                         ▼
                    FastAPI API
                         │
                         ▼
                    LangGraph
                         │
                         ▼
                    Retrieve
                         │
                         ▼
                     Pinecone
                         │
                         ▼
                  Relevant Chunks
                         │
                         ▼
                  Build Context
                         │
                         ▼
                   LLM Factory
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
     Groq              OpenAI            Gemini
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                  Generate Answer
                         │
                         ▼
                    FastAPI
                         │
                         ▼
                       React
```

---

# 8.14 Why LangGraph is useful now

Currently our graph is simple:

```text
START
  ↓
Retrieve
  ↓
Context
  ↓
Generate
  ↓
END
```

But later we can make it intelligent:

```text
                         START
                           │
                           ▼
                       Retrieve
                           │
                           ▼
                   Relevant enough?
                    /           \
                  YES            NO
                   │              │
                   ▼              ▼
             Generate       Rewrite Query
                   │              │
                   │              ▼
                   │           Retrieve
                   │              │
                   └──────┬───────┘
                          ▼
                    Validate Answer
                          │
                    ┌─────┴─────┐
                    ▼           ▼
                  Good        Bad
                    │           │
                    ▼           ▼
                   END        Retry
```

That is where LangGraph becomes significantly more powerful than simply calling an LLM.

---

## Next Step — Step 9: Chat History + Conversation Memory

At the moment:

```text
Question 1
   ↓
Answer 1

Question 2
   ↓
Answer 2
```

The system doesn't remember Question 1.

We'll next add:

```text
Supabase PostgreSQL

users
documents
chat_sessions
chat_messages
```

so the conversation becomes:

```text
User:
"What is FastAPI?"

AI:
"FastAPI is..."

User:
"Who created it?"

AI:
"Sebastián Ramírez..."

User:
"What year?"

AI:
"FastAPI was initially released in 2018..."
```

And we'll connect that history to **LangGraph state**, while keeping the database as the persistent source of truth.


# Step 9 — Chat History + Conversation Memory

Now we make our Document Q&A Bot behave like a real chat application.

Currently:

```text
Question 1 → Answer 1
Question 2 → Answer 2
```

The second question doesn't know what the user said previously.

We'll change it to:

```text
Question 1
   ↓
Answer 1
   ↓
Question 2
   ↓
Previous conversation + Question 2
   ↓
Answer 2
```

And we'll store the conversation in **Supabase PostgreSQL**.

---

# 9.1 Database design

We'll add two tables:

```text
users
  │
  └── chat_sessions
          │
          └── chat_messages
```

Conceptually:

```text
users
────────────────
id
name
email
password_hash
created_at


chat_sessions
────────────────
id
user_id
title
created_at


chat_messages
────────────────
id
session_id
role
content
created_at
```

Relationship:

```text
User
 │
 │ 1
 │
 │ many
 ▼
ChatSession
 │
 │ 1
 │
 │ many
 ▼
ChatMessage
```

---

# 9.2 Update database models

Open:

```text
app/database/models.py
```

Add:

```python
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from sqlalchemy.orm import relationship

from sqlalchemy.sql import func

from app.database.connection import Base
```

Then add these models below `Document`.

```python
class ChatSession(Base):

    __tablename__ = "chat_sessions"

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

    title = Column(
        String(255),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan"
    )
```

Now the message model:

```python
class ChatMessage(Base):

    __tablename__ = "chat_messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    session_id = Column(
        Integer,
        ForeignKey(
            "chat_sessions.id"
        ),
        nullable=False,
        index=True
    )

    role = Column(
        String(20),
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    session = relationship(
        "ChatSession",
        back_populates="messages"
    )
```

---

# 9.3 Why `role`?

Each message needs to tell us who produced it.

We'll use:

```text
user
assistant
```

Example:

```text
chat_messages

id | session_id | role      | content
---|------------|-----------|--------------------
1  | 10         | user      | What is FastAPI?
2  | 10         | assistant | FastAPI is...
3  | 10         | user      | Why use it?
4  | 10         | assistant | It is useful because...
```

This is exactly what we'll eventually send to the LLM as conversation history.

---

# 9.4 Important database migration point

Because your application currently uses:

```python
Base.metadata.create_all(
    bind=engine
)
```

new tables can be created automatically during development.

Restart:

```bash
uv run fastapi dev app/main.py
```

You should now see these tables in Supabase:

```text
users
documents
chat_sessions
chat_messages
```

For production, we'll later replace `create_all()` with **Alembic migrations**.

---

# 9.5 Create Chat Session schemas

Create:

```text
app/schemas/chat_session.py
```

```python
from datetime import datetime

from pydantic import BaseModel


class ChatSessionCreate(BaseModel):

    title: str | None = None


class ChatSessionResponse(BaseModel):

    id: int
    title: str | None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
```

---

# 9.6 Create Chat Session API

Create:

```text
app/api/chat_sessions.py
```

```python
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database.connection import get_db

from app.database.models import (
    User,
    ChatSession,
)

from app.schemas.chat_session import (
    ChatSessionCreate,
    ChatSessionResponse,
)


router = APIRouter(
    prefix="/api/chat/sessions",
    tags=["Chat Sessions"]
)


@router.post(
    "",
    response_model=ChatSessionResponse
)
def create_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    session = ChatSession(
        user_id=current_user.id,
        title=session_data.title
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session
```

---

# 9.7 Get user's chat sessions

Add to the same file:

```python
@router.get(
    "",
    response_model=list[ChatSessionResponse]
)
def get_sessions(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    sessions = (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id
            == current_user.id
        )
        .order_by(
            ChatSession.created_at.desc()
        )
        .all()
    )

    return sessions
```

Notice:

```python
ChatSession.user_id == current_user.id
```

Again, this is important for multi-user security.

Student A should never see Student B's chat sessions.

---

# 9.8 Get conversation history

Add:

```python
from app.database.models import (
    User,
    ChatSession,
    ChatMessage,
)
```

Then:

```python
@router.get(
    "/{session_id}/messages"
)
def get_messages(
    session_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id
            == current_user.id
        )
        .first()
    )

    if not session:

        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id
            == session_id
        )
        .order_by(
            ChatMessage.created_at.asc()
        )
        .all()
    )

    return messages
```

Now React can request:

```http
GET /api/chat/sessions/10/messages
```

and receive:

```json
[
    {
        "role": "user",
        "content": "What is FastAPI?"
    },
    {
        "role": "assistant",
        "content": "FastAPI is..."
    }
]
```

---

# 9.9 Register the router

Open:

```text
app/main.py
```

Add:

```python
from app.api.chat_sessions import (
    router as chat_sessions_router
)
```

Then:

```python
app.include_router(
    chat_sessions_router
)
```

Your API structure is now:

```text
/api/auth
/api/documents
/api/search
/api/chat
/api/chat/sessions
```

---

# 9.10 Update ChatRequest

Now we need to tell the chat API which conversation we're using.

Open:

```text
app/schemas/chat.py
```

Change:

```python
class ChatRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1
    )

    session_id: int | None = None

    provider: str | None = None

    model: str | None = None

    temperature: float = Field(
        default=0.2,
        ge=0,
        le=2
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20
    )
```

Now the request can be:

```json
{
    "session_id": 10,
    "question": "What is FastAPI?",
    "provider": "groq",
    "model": "qwen/qwen3-32b",
    "temperature": 0.2,
    "top_k": 5
}
```

---

# 9.11 Add conversation history to LangGraph State

Open:

```text
app/graph/state.py
```

Update:

```python
from typing import TypedDict


class RAGState(TypedDict, total=False):

    user_id: int

    session_id: int

    question: str

    top_k: int

    provider: str

    model: str | None

    temperature: float

    chat_history: list

    retrieved_chunks: list

    context: str

    answer: str

    sources: list
```

We have added:

```python
chat_history: list
```

Now LangGraph knows about previous messages.

---

# 9.12 Create History Node

Open:

```text
app/graph/nodes.py
```

Add:

```python
from app.database.connection import SessionLocal

from app.database.models import (
    ChatMessage,
)


def load_history_node(state):

    session_id = state.get(
        "session_id"
    )

    if not session_id:

        return {
            "chat_history": []
        }

    db = SessionLocal()

    try:

        messages = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id
                == session_id
            )
            .order_by(
                ChatMessage.created_at.asc()
            )
            .all()
        )

        history = []

        for message in messages:

            history.append({
                "role": message.role,
                "content": message.content
            })

        return {
            "chat_history": history
        }

    finally:

        db.close()
```

---

# 9.13 Update the Graph

Our workflow was:

```text
START
  ↓
Retrieve
  ↓
Build Context
  ↓
Generate
  ↓
END
```

Now:

```text
START
  ↓
Load History
  ↓
Retrieve
  ↓
Build Context
  ↓
Generate
  ↓
END
```

Open:

```text
app/graph/workflow.py
```

Change it to:

```python
from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from app.graph.state import RAGState

from app.graph.nodes import (
    load_history_node,
    retrieve_node,
    build_context_node,
    generate_answer_node,
)


def create_rag_graph():

    graph = StateGraph(RAGState)

    graph.add_node(
        "load_history",
        load_history_node
    )

    graph.add_node(
        "retrieve",
        retrieve_node
    )

    graph.add_node(
        "build_context",
        build_context_node
    )

    graph.add_node(
        "generate_answer",
        generate_answer_node
    )

    graph.add_edge(
        START,
        "load_history"
    )

    graph.add_edge(
        "load_history",
        "retrieve"
    )

    graph.add_edge(
        "retrieve",
        "build_context"
    )

    graph.add_edge(
        "build_context",
        "generate_answer"
    )

    graph.add_edge(
        "generate_answer",
        END
    )

    return graph.compile()
```

---

# 9.14 Use history in the LLM

Now modify:

```text
generate_answer_node()
```

We want the LLM to see previous conversation.

```python
def generate_answer_node(state):

    question = state["question"]

    context = state.get(
        "context",
        ""
    )

    chat_history = state.get(
        "chat_history",
        []
    )

    provider = state.get(
        "provider",
        "groq"
    )

    model = state.get(
        "model"
    )

    temperature = state.get(
        "temperature",
        0.2
    )

    llm = get_llm(
        provider=provider,
        model=model,
        temperature=temperature
    )

    history_text = ""

    for message in chat_history:

        history_text += (
            f"{message['role']}: "
            f"{message['content']}\n"
        )

    prompt = f"""
You are a helpful document
question-answering assistant.

Answer using the supplied document context.

Do not invent information.

If the answer is not available in the
documents, say that you could not find
the answer in the uploaded documents.

Previous Conversation:
========================
{history_text}
========================

Document Context:
========================
{context}
========================

Current Question:
{question}

Answer:
"""

    response = llm.invoke(prompt)

    return {
        "answer": response.content
    }
```

Now the LLM gets:

```text
Previous Conversation
        +
Document Context
        +
Current Question
```

---

# 9.15 Save messages to PostgreSQL

We also need to save the current question and answer.

Open:

```text
app/api/chat.py
```

Import:

```python
from app.database.models import (
    User,
    ChatSession,
    ChatMessage,
)
```

Then after the graph returns its answer:

```python
session_id = request.session_id
```

If there isn't a session, create one:

```python
if session_id:

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id
            == current_user.id
        )
        .first()
    )

    if not session:

        raise HTTPException(
            status_code=404,
            detail="Chat session not found"
        )

else:

    session = ChatSession(
        user_id=current_user.id,
        title=request.question[:100]
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    session_id = session.id
```

Then save the user message:

```python
user_message = ChatMessage(
    session_id=session_id,
    role="user",
    content=request.question
)

db.add(user_message)
```

And save the AI response:

```python
assistant_message = ChatMessage(
    session_id=session_id,
    role="assistant",
    content=result["answer"]
)

db.add(assistant_message)

db.commit()
```

---

# 9.16 Updated Chat API flow

Your `/api/chat` now works like this:

```text
POST /api/chat
       │
       ▼
Validate JWT
       │
       ▼
Check Chat Session
       │
       ▼
Save User Question
       │
       ▼
     LangGraph
       │
       ├── Load History
       │
       ├── Retrieve Pinecone
       │
       ├── Build Context
       │
       └── Generate Answer
               │
               ▼
         Groq/OpenAI/Gemini/
            Claude/etc.
               │
               ▼
         Save AI Answer
               │
               ▼
            Response
```

---

# 9.17 Very important: conversation history vs RAG

Students often confuse these two.

### Conversation memory

Stored in:

```text
Supabase PostgreSQL
```

Example:

```text
"What is FastAPI?"
"Why is it used?"
"Give me an example."
```

### Knowledge

Stored in:

```text
Pinecone
```

Example:

```text
python.pdf
fastapi.pdf
rag.pdf
```

So:

```text
                 RAG
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
Conversation              Knowledge
   Memory                   Base
       │                     │
       ▼                     ▼
   Supabase               Pinecone
 PostgreSQL
```

This separation is exactly what we want.

---

# 9.18 Current complete architecture

```text
                         React
                           │
                           ▼
                        FastAPI
                           │
                  ┌────────┴────────┐
                  │                 │
                  ▼                 ▼
              Documents           Chat
                  │                 │
                  ▼                 ▼
             Local/S3           LangGraph
                  │                 │
                  ▼          ┌──────┴──────┐
             Text/Chunks     │             │
                  │          ▼             ▼
                  ▼       History       Retrieval
              Embeddings     │             │
                  │          ▼             ▼
                  ▼       Supabase      Pinecone
              Pinecone    PostgreSQL        │
                               │             │
                               └──────┬──────┘
                                      ▼
                                  Context
                                      │
                                      ▼
                                 LLM Factory
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
                  Groq             OpenAI             Gemini
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      ▼
                                  AI Answer
                                      │
                                      ▼
                                  Supabase
                                      │
                                      ▼
                                    React
```

---

## What we've completed

```text
✅ Step 1   FastAPI
✅ Step 2   Supabase + JWT Authentication
✅ Step 3   Document Upload
✅ Step 4   PDF/DOCX/TXT Processing
✅ Step 5   Embeddings + Pinecone
✅ Step 6   Semantic Search
✅ Step 7   Multi-LLM API
             ├── Groq
             ├── OpenAI
             ├── Gemini
             └── Anthropic
✅ Step 8   LangGraph RAG Workflow
✅ Step 9   Chat Sessions + History
```

### Next: Step 10 — Production-quality RAG

The next improvement should be **not another API endpoint**, but making the RAG workflow intelligent:

```text
User Question
      ↓
Conversation History
      ↓
Query Understanding / Rewriting
      ↓
Pinecone Retrieval
      ↓
Relevance Check
      ↓
     ┌───────────────┐
     │ Relevant?     │
     └──────┬────────┘
        YES │ NO
            │
       ┌────┴────┐
       ▼         ▼
    Generate   Rewrite
       │         │
       │         └──→ Retrieve again
       ▼
  Answer Validation
       │
       ▼
    Sources
       │
       ▼
    Response
```

Then we'll add **streaming responses**, **citations/page references**, **document management/delete**, and finally prepare the backend for the React frontend and AWS deployment.
