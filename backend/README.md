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
