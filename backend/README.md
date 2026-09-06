# Step 10 — Production-Quality RAG: Query Rewriting + Relevance Check

Now we'll improve the basic RAG:

```text
Question
   ↓
Pinecone
   ↓
LLM
   ↓
Answer
```

into a more reliable workflow:

```text
User Question
      ↓
Conversation History
      ↓
Query Rewriting
      ↓
Pinecone Retrieval
      ↓
Relevance Check
      │
   ┌──┴───┐
   │      │
  YES     NO
   │      │
   ▼      ▼
Generate  Rewrite
   │      │
   │      └──────→ Retrieve again
   ▼
Validate Answer
   ↓
Answer + Sources
```

This is where **LangGraph** starts becoming really useful.

---

# 10.1 Why Query Rewriting?

Consider this conversation:

```text
User:
What is FastAPI?

AI:
FastAPI is a Python framework...

User:
What are its advantages?

AI:
...
```

The second question:

```text
"What are its advantages?"
```

is ambiguous by itself.

Pinecone may perform better if we transform it into:

```text
"What are the advantages of FastAPI?"
```

So we introduce a **query rewriting node**.

---

# 10.2 Update the State

Open:

```text
backend/app/graph/state.py
```

Change it to:

```python
from typing import TypedDict


class RAGState(TypedDict, total=False):

    # =========================
    # User
    # =========================

    user_id: int

    session_id: int

    # =========================
    # Questions
    # =========================

    question: str

    rewritten_question: str

    # =========================
    # Retrieval
    # =========================

    top_k: int

    retrieved_chunks: list

    context: str

    # =========================
    # Conversation
    # =========================

    chat_history: list

    # =========================
    # LLM
    # =========================

    provider: str

    model: str | None

    temperature: float

    # =========================
    # Output
    # =========================

    answer: str

    sources: list

    # =========================
    # Validation
    # =========================

    is_relevant: bool

    retry_count: int
```

We've added:

```python
rewritten_question
```

and:

```python
is_relevant
retry_count
```

---

# 10.3 Create Query Rewriting Node

Open:

```text
backend/app/graph/nodes.py
```

Add:

```python
def rewrite_query_node(state):

    question = state["question"]

    chat_history = state.get(
        "chat_history",
        []
    )

    # If there is no conversation history,
    # no rewriting is necessary.
    if not chat_history:

        return {
            "rewritten_question": question
        }

    provider = state.get(
        "provider",
        "groq"
    )

    model = state.get(
        "model"
    )

    temperature = state.get(
        "temperature",
        0
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
You are a search query rewriting assistant.

Rewrite the user's current question so that
it can be understood independently.

Use the conversation history to resolve
references such as:

- it
- this
- that
- they
- them
- its
- the above

Do not answer the question.

Return ONLY the rewritten search query.

Conversation:
----------------
{history_text}
----------------

Current Question:
{question}

Rewritten Query:
"""

    response = llm.invoke(prompt)

    rewritten_question = (
        response.content.strip()
    )

    return {
        "rewritten_question": rewritten_question
    }
```

---

# 10.4 Example

Conversation:

```text
User:
What is FastAPI?

AI:
FastAPI is a Python framework...

User:
What are its advantages?
```

The node produces:

```text
What are the advantages of FastAPI?
```

Then Pinecone searches using:

```python
state["rewritten_question"]
```

instead of:

```python
state["question"]
```

---

# 10.5 Update Retrieval Node

Find:

```python
def retrieve_node(state):
```

Change the beginning to:

```python
def retrieve_node(state):

    question = state.get(
        "rewritten_question",
        state["question"]
    )

    user_id = state["user_id"]

    top_k = state.get(
        "top_k",
        5
    )

    results = search_chunks(
        query=question,
        user_id=user_id,
        top_k=top_k
    )
```

The rest of the function can remain the same.

Now:

```text
Original Question
       ↓
Query Rewriter
       ↓
Rewritten Question
       ↓
Pinecone
```

---

# 10.6 Add Relevance Checking

Retrieval doesn't guarantee that the returned documents actually answer the question.

For example:

```text
Question:
"What is FastAPI?"
```

Pinecone could return weak matches:

```text
Python history
Python syntax
Python installation
```

We need to check:

```text
Are these chunks actually relevant?
```

Create:

```python
def check_relevance_node(state):

    question = state.get(
        "rewritten_question",
        state["question"]
    )

    context = state.get(
        "context",
        ""
    )

    if not context:

        return {
            "is_relevant": False
        }

    provider = state.get(
        "provider",
        "groq"
    )

    model = state.get(
        "model"
    )

    llm = get_llm(
        provider=provider,
        model=model,
        temperature=0
    )

    prompt = f"""
You are a document relevance evaluator.

Determine whether the provided context
contains information that can help answer
the question.

Return ONLY one word:

YES

or

NO

Question:
----------------
{question}

Context:
----------------
{context}

Decision:
"""

    response = llm.invoke(prompt)

    decision = (
        response.content
        .strip()
        .upper()
    )

    return {
        "is_relevant": decision == "YES"
    }
```

---

# 10.7 Add Conditional Routing

Now LangGraph can make decisions.

We want:

```text
Retrieve
   ↓
Build Context
   ↓
Check Relevance
   │
   ├── YES → Generate Answer
   │
   └── NO  → Rewrite Query
```

But if rewriting sends us back to retrieval, we need to avoid an infinite loop.

We'll use:

```text
retry_count
```

---

# 10.8 Create Routing Function

In:

```text
backend/app/graph/workflow.py
```

add:

```python
def relevance_router(state):

    is_relevant = state.get(
        "is_relevant",
        False
    )

    retry_count = state.get(
        "retry_count",
        0
    )

    if is_relevant:

        return "generate_answer"

    if retry_count >= 1:

        return "generate_answer"

    return "retry_retrieval"
```

This means:

```text
Relevant?
   │
   ├── YES → Generate
   │
   └── NO
       │
       ├── retry < 1 → Retry
       │
       └── retry >= 1 → Generate anyway
```

---

# 10.9 Add Retry Node

In `nodes.py`:

```python
def retry_retrieval_node(state):

    retry_count = state.get(
        "retry_count",
        0
    )

    return {
        "retry_count": retry_count + 1
    }
```

This lets the graph keep track of how many retrieval attempts we've made.

---

# 10.10 Build the New Graph

Replace `workflow.py` with:

```python
from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from app.graph.state import RAGState

from app.graph.nodes import (
    load_history_node,
    rewrite_query_node,
    retrieve_node,
    build_context_node,
    check_relevance_node,
    retry_retrieval_node,
    generate_answer_node,
)


def relevance_router(state):

    is_relevant = state.get(
        "is_relevant",
        False
    )

    retry_count = state.get(
        "retry_count",
        0
    )

    if is_relevant:

        return "generate_answer"

    if retry_count >= 1:

        return "generate_answer"

    return "retry_retrieval"


def create_rag_graph():

    graph = StateGraph(RAGState)

    # =========================
    # Nodes
    # =========================

    graph.add_node(
        "load_history",
        load_history_node
    )

    graph.add_node(
        "rewrite_query",
        rewrite_query_node
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
        "check_relevance",
        check_relevance_node
    )

    graph.add_node(
        "retry_retrieval",
        retry_retrieval_node
    )

    graph.add_node(
        "generate_answer",
        generate_answer_node
    )

    # =========================
    # Initial workflow
    # =========================

    graph.add_edge(
        START,
        "load_history"
    )

    graph.add_edge(
        "load_history",
        "rewrite_query"
    )

    graph.add_edge(
        "rewrite_query",
        "retrieve"
    )

    graph.add_edge(
        "retrieve",
        "build_context"
    )

    graph.add_edge(
        "build_context",
        "check_relevance"
    )

    # =========================
    # Conditional routing
    # =========================

    graph.add_conditional_edges(
        "check_relevance",
        relevance_router,
        {
            "generate_answer":
                "generate_answer",

            "retry_retrieval":
                "retry_retrieval",
        }
    )

    # =========================
    # Retry
    # =========================

    graph.add_edge(
        "retry_retrieval",
        "rewrite_query"
    )

    # =========================
    # End
    # =========================

    graph.add_edge(
        "generate_answer",
        END
    )

    return graph.compile()
```

---

# 10.11 Our LangGraph is now intelligent

The graph is:

```text
                    START
                      │
                      ▼
                Load History
                      │
                      ▼
                Rewrite Query
                      │
                      ▼
                  Retrieve
                      │
                      ▼
                Build Context
                      │
                      ▼
              Check Relevance
                      │
                 ┌────┴────┐
                 │         │
                YES        NO
                 │         │
                 ▼         ▼
              Generate   Retry
                 │         │
                 │         ▼
                 │      Rewrite
                 │         │
                 │         ▼
                 │      Retrieve
                 │
                 ▼
                  END
```

---

# 10.12 One problem with the retry design

There's a subtle issue.

Currently:

```text
retry_retrieval
       ↓
rewrite_query
       ↓
retrieve
```

The second rewrite could produce the same query.

A better production version would eventually add:

```text
Query Rewriter
      ↓
Alternative Query
```

or use a dedicated retrieval strategy.

For our beginner-to-intermediate project, **one retry is enough**.

---

# 10.13 Add answer validation

We can add another quality-control step.

Current:

```text
Generate Answer
      ↓
END
```

Better:

```text
Generate Answer
      ↓
Validate Answer
      │
   ┌──┴──┐
   │     │
 GOOD   BAD
   │     │
   ▼     ▼
 END    Retry
```

Add:

```python
def validate_answer_node(state):

    answer = state.get(
        "answer",
        ""
    )

    context = state.get(
        "context",
        ""
    )

    question = state.get(
        "question",
        ""
    )

    provider = state.get(
        "provider",
        "groq"
    )

    model = state.get(
        "model"
    )

    llm = get_llm(
        provider=provider,
        model=model,
        temperature=0
    )

    prompt = f"""
You are checking a RAG answer.

Determine whether the answer is supported
by the supplied document context.

Return ONLY:

YES

or

NO

Question:
{question}

Context:
{context}

Answer:
{answer}

Decision:
"""

    response = llm.invoke(prompt)

    return {
        "answer_valid": (
            response.content
            .strip()
            .upper()
            == "YES"
        )
    }
```

For that, add to state:

```python
answer_valid: bool
```

---

# 10.14 Production RAG architecture

We are now moving toward:

```text
                              User
                                │
                                ▼
                              React
                                │
                                ▼
                             FastAPI
                                │
                                ▼
                           LangGraph
                                │
                                ▼
                         Load Conversation
                                │
                                ▼
                         Rewrite Question
                                │
                                ▼
                           Pinecone
                                │
                                ▼
                         Retrieve Chunks
                                │
                                ▼
                        Relevance Check
                           │         │
                         Good       Bad
                           │         │
                           │      Retry
                           │         │
                           ▼         └──→ Retrieve
                         Context
                           │
                           ▼
                       LLM Factory
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
           Groq          OpenAI        Gemini
             │             │             │
             └─────────────┼─────────────┘
                           │
                           ▼
                     Generate Answer
                           │
                           ▼
                    Answer Validation
                           │
                           ▼
                     Sources/Citations
                           │
                           ▼
                          React
```

---

# Step 10 Complete

We now have:

```text
✅ Multi-user authentication
✅ Supabase PostgreSQL
✅ Document upload
✅ Local document storage
✅ Document processing
✅ Chunking
✅ Embeddings
✅ Pinecone
✅ Semantic search
✅ Multi-provider LLM
   ├── Groq
   ├── OpenAI
   ├── Gemini
   └── Anthropic
✅ LangGraph
✅ Chat sessions
✅ Persistent chat history
✅ Query rewriting
✅ Relevance checking
✅ Retrieval retry
```

## Next Step — Step 11: Proper Chat API + Streaming

The next important step is to make the API behave like a real ChatGPT-style application:

```text
React
  │
  │ POST /api/chat
  ▼
FastAPI
  │
  ▼
LangGraph
  │
  ▼
LLM
  │
  │ token by token
  ▼
StreamingResponse
  │
  ▼
React Chat UI
```

We'll implement **streaming**, so instead of waiting 5–10 seconds for the complete answer, the frontend can receive:

```text
FastAPI
FastAPI is
FastAPI is a
FastAPI is a modern
FastAPI is a modern Python
...
```

This will also prepare the backend cleanly for the React frontend.
