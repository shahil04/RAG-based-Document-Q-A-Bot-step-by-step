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
        "answer": content_to_text(
            response.content
        )
    }