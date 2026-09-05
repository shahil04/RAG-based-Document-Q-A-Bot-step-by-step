from fastapi import FastAPI

from app.api.health import router as health_router
from app.core.config import APP_NAME, APP_VERSION

app = FastAPI(
    title=APP_NAME,
    description="RAG Based Document Question Answering System",
    version=APP_VERSION,
)
app.include_router(health_router)


@app.get("/")
def root():
    return {
        "message": "Document Q&A API is running",
        "version": APP_VERSION
    }