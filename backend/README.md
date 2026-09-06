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
