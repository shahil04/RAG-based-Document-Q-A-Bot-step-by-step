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