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
