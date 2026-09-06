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