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
