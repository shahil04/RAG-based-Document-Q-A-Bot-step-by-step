from fastapi import APIRouter, Depends

from app.api.auth import get_current_user
from app.database.models import User
from app.rag.vector_store import search_chunks
from app.schemas.search import (
    SearchRequest,
    SearchResult
)


router = APIRouter(
    prefix="/api/search",
    tags=["Search"]
)


@router.post(
    "",
    response_model=list[SearchResult]
)
def semantic_search(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_user)
):

    results = search_chunks(
        query=search_request.query,
        user_id=current_user.id,
        top_k=search_request.top_k
    )

    search_results = []

    for match in results["matches"]:

        metadata = match.get("metadata", {})

        search_results.append(
            SearchResult(
                text=metadata.get("text", ""),
                score=match.get("score", 0),
                document_id=metadata.get(
                    "document_id",
                    ""
                ),
                filename=metadata.get(
                    "filename"
                ),
                page=metadata.get(
                    "page"
                )
            )
        )

    return search_results