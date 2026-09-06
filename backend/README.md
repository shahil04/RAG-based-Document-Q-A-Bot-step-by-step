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
