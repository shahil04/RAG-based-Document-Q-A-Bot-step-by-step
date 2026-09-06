

# from pinecone import Pinecone
# from app.core.config import (PINECONE_API_KEY,PINECONE_INDEX_NAME,)


# def get_pinecone_client():
#     if not PINECONE_API_KEY:
#         raise ValueError("PINECONE_API_KEY is not configured")

#     return Pinecone(
#         api_key=PINECONE_API_KEY
#     )


# def get_index():
#     pc = get_pinecone_client()

#     return pc.Index(
#         PINECONE_INDEX_NAME
#     )

from uuid import uuid4

from pinecone import Pinecone

from app.core.config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
)
from app.rag.embeddings import get_embedding_model


embedding_model = get_embedding_model()


def get_pinecone_client():

    if not PINECONE_API_KEY:
        raise ValueError(
            "PINECONE_API_KEY is not configured"
        )

    return Pinecone(
        api_key=PINECONE_API_KEY
    )


def get_index():

    pc = get_pinecone_client()

    return pc.Index(
        PINECONE_INDEX_NAME
    )


def store_chunks(
    chunks,
    user_id: int,
    document_id: int
):

    index = get_index()

    vectors = []

    for chunk in chunks:

        text = chunk.page_content

        vector = embedding_model.embed_query(text)

        metadata = {
            "user_id": str(user_id),
            "document_id": str(document_id),
            "text": text,
            "source": chunk.metadata.get(
                "source",
                ""
            ),
            "page": chunk.metadata.get(
                "page",
                0
            )
        }

        vectors.append(
            {
                "id": str(uuid4()),
                "values": vector,
                "metadata": metadata
            }
        )

    index.upsert(
        vectors=vectors
    )

    return len(vectors)