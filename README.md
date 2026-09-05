We’ll build the **RAG-based Document Q&A Bot step by step**, starting only with the **FastAPI backend**.

We will not jump into React, AWS, or RAG yet. First, we’ll make a clean backend foundation.

# Step 1 — Backend Setup

### Final technology stack

```text
Frontend       → React.js
Backend        → FastAPI
LLM            → Groq
LLM Framework  → LangChain
Workflow       → LangGraph
Database       → Supabase PostgreSQL
Vector Search  → pgvector
Authentication → JWT
Deployment     → AWS
Package Tool   → uv
```

For now:

```text
                BACKEND
                   │
                   ▼
              FastAPI
                   │
          ┌────────┴────────┐
          ▼                 ▼
      API Routes        Services
          │                 │
          └────────┬────────┘
                   ▼
              LangChain
                   │
                   ▼
                Groq
```

---

# 1. Create Project

Open terminal:

```bash
mkdir document-qa-bot
cd document-qa-bot
```

Create backend:

```bash
mkdir backend
cd backend
```

Initialize `uv`:

```bash
uv init
```

You should get something like:

```text
backend/
├── .python-version
├── pyproject.toml
└── README.md
```

---

# 2. Create Virtual Environment

```bash
uv venv
```

Activate it.

### Windows

```bash
.venv\Scripts\activate
```

### Linux/Mac

```bash
source .venv/bin/activate
```

Check:

```bash
python --version
```

---

# 3. Install FastAPI

Install the basic backend dependencies first:

```bash
uv add "fastapi[standard]"
```

Then:

```bash
uv add python-dotenv
```

Later we will add:

```text
LangChain
LangGraph
Groq
Supabase
PostgreSQL
JWT
PDF processing
Embeddings
```

But **don't install everything at once**. We'll introduce each component when we need it.

---

# 4. Create Backend Folder Structure

Inside `backend`, create:

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
│   │   └── health.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   │
│   ├── schemas/
│   │   └── __init__.py
│   │
│   ├── services/
│   │   └── __init__.py
│   │
│   ├── database/
│   │   └── __init__.py
│   │
│   ├── rag/
│   │   └── __init__.py
│   │
│   └── graph/
│       └── __init__.py
│
├── .env
├── .gitignore
├── pyproject.toml
└── README.md
```

### Why this structure?

We are separating responsibilities:

```text
app/
│
├── api/         → API endpoints
├── core/        → configuration/security
├── schemas/     → request/response models
├── services/    → business logic
├── database/    → PostgreSQL/Supabase
├── rag/         → RAG components
└── graph/       → LangGraph workflow
```

This is much better than putting everything inside `main.py`.

---

# 5. Create First FastAPI Application

Create:

```text
app/main.py
```

Add:

```python
from fastapi import FastAPI

app = FastAPI(
    title="Document Q&A API",
    description="RAG Based Document Question Answering System",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Document Q&A API is running"
    }
```

---

# 6. Run FastAPI

From the `backend` folder:

```bash
uv run fastapi dev app/main.py
```

You should see something similar to:

```text
Server started at http://127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000
```

Response:

```json
{
    "message": "Document Q&A API is running"
}
```

---

# 7. FastAPI Swagger Documentation

Now open:

```text
http://127.0.0.1:8000/docs
```

You should see the FastAPI Swagger UI.

This is one of the reasons FastAPI is excellent for our project.

Our frontend will eventually communicate with these APIs:

```text
React
  │
  │ HTTP Request
  ▼
FastAPI
  │
  ├── Authentication
  ├── Documents
  ├── Chat
  └── RAG
```

---

# 8. Create Health Check API

Now let's create our first proper API route.

Create:

```text
app/api/health.py
```

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/api",
    tags=["Health"]
)


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "document-qa-backend"
    }
```

---

# 9. Connect Health API to Main Application

Update:

```text
app/main.py
```

```python
from fastapi import FastAPI

from app.api.health import router as health_router


app = FastAPI(
    title="Document Q&A API",
    description="RAG Based Document Question Answering System",
    version="1.0.0",
)


app.include_router(health_router)


@app.get("/")
def root():
    return {
        "message": "Document Q&A API is running"
    }
```

---

# 10. Test Health API

Restart the server if necessary:

```bash
uv run fastapi dev app/main.py
```

Open:

```text
http://127.0.0.1:8000/api/health
```

Expected:

```json
{
    "status": "healthy",
    "service": "document-qa-backend"
}
```

Also check Swagger:

```text
http://127.0.0.1:8000/docs
```

You should now see:

```text
Document Q&A API

GET /
GET /api/health
```

---

# 11. Add Environment Configuration

Now create:

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

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)
```

---

# 12. `.env`

Create:

```text
backend/.env
```

For now:

```env
APP_NAME=Document Q&A API
APP_VERSION=1.0.0

GROQ_API_KEY=your_groq_api_key
```

**Don't commit `.env` to GitHub.**

---

# 13. `.gitignore`

Create:

```text
backend/.gitignore
```

```gitignore
# Virtual environment
.venv/

# Environment variables
.env

# Python
__pycache__/
*.py[cod]

# IDE
.vscode/
.idea/

# Testing
.pytest_cache/

# OS
.DS_Store
Thumbs.db
```

---

# 14. Update `main.py` to Use Configuration

```python
from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import APP_NAME, APP_VERSION


app = FastAPI(
    title=APP_NAME,
    description="RAG Based Document Question Answering System",
    version=APP_VERSION,
)


app.include_router(health_router)


@app.get("/")
def root():
    return {
        "message": "Document Q&A API is running",
        "version": APP_VERSION
    }
```

---

# 15. Current Architecture

At this point we have:

```text
document-qa-bot/
│
└── backend/
    │
    ├── app/
    │   │
    │   ├── main.py
    │   │
    │   ├── api/
    │   │   ├── __init__.py
    │   │   └── health.py
    │   │
    │   ├── core/
    │   │   ├── __init__.py
    │   │   └── config.py
    │   │
    │   ├── schemas/
    │   ├── services/
    │   ├── database/
    │   ├── rag/
    │   └── graph/
    │
    ├── .env
    ├── .gitignore
    ├── pyproject.toml
    └── README.md
```

And our request flow is:

```text
Browser
   │
   ▼
FastAPI
   │
   ├── / 
   │
   └── /api/health
```

---

# What We Build Next

We'll develop the backend in this order:

### Step 1 ✅

**FastAPI project setup**

### Step 2

**Student/User Registration & Login**

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

### Step 3

**Supabase PostgreSQL connection**

```text
FastAPI
   │
   ▼
Supabase
   │
   ▼
PostgreSQL
```

### Step 4

**JWT authentication**

### Step 5

**Document upload**

```text
PDF
 ↓
FastAPI
 ↓
Document processing
```

### Step 6

**PDF text extraction**

### Step 7

**Chunking**

```text
Document
 ↓
Text
 ↓
Chunks
```

### Step 8

**Embeddings**

```text
Chunks
 ↓
Embedding Model
 ↓
Vectors
```

### Step 9

**Supabase pgvector**

```text
PostgreSQL
   +
pgvector
   ↓
Vector Search
```

### Step 10

**LangChain**

### Step 11

**LangGraph**

```text
Question
   ↓
Retrieve
   ↓
Context
   ↓
Generate
   ↓
Answer
```

### Step 12

**Chat API**

```text
POST /api/chat
```

### Step 13

**Connect React frontend**

### Step 14

**Docker**

### Step 15

**AWS deployment**

---

## Next: Authentication

Since this is a real-world Document Q&A application, I recommend we **do User Registration/Login before RAG**.

We'll build:

```text
                    FastAPI
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
        Register               Login
             │                   │
             ▼                   ▼
        PostgreSQL          Verify User
                                 │
                                 ▼
                            JWT Token
                                 │
                                 ▼
                         Protected APIs
```

Then every document and chat session can belong to the logged-in user.
