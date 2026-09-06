from app.rag.vector_store import search_chunks
from app.llm.factory import get_llm


def content_to_text(content) -> str:

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if text:
                    text_parts.append(str(text))

        return "\n".join(text_parts)

    return str(content)


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

# memorynode

from app.database.connection import SessionLocal
from app.database.models import (ChatMessage,)

def load_history_node(state):
    session_id = state.get("session_id")
    if not session_id:
        return {"chat_history": []}

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