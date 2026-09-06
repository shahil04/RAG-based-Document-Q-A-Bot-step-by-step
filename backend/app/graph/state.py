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