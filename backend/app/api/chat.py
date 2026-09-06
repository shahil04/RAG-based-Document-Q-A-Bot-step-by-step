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


def _content_to_text(content) -> str:

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

    answer = _content_to_text(
        response.content
    )

    # =========================
    # 6. Return response
    # =========================

    return ChatResponse(
        answer=answer,
        provider=provider,
        model=model or "default",
        sources=sources
    )