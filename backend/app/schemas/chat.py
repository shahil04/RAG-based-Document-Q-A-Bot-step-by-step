from pydantic import BaseModel, Field
class ChatRequest(BaseModel):

    question: str = Field(
        ...,
        min_length=1
    )

    session_id: int | None = None

    provider: str | None = None

    model: str | None = None

    temperature: float = Field(
        default=0.2,
        ge=0,
        le=2
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=20
    )
class ChatResponse(BaseModel):
    answer: str
    provider: str
    model: str
    sources: list