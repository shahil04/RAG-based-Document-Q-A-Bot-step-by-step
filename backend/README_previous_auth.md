

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
