from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    text: str
    score: float
    document_id: str
    filename: str | None = None
    page: int | None = None