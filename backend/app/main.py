from fastapi import FastAPI
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.core.config import (APP_NAME,APP_VERSION)
from app.api.search import router as search_router
from app.database.connection import (Base,engine)
from app.database import models
from app.api.chat import router as chat_router
from app.api.chat_sessions import (router as chat_sessions_router)
# Because the users table may already exist, create_all() will create the new documents table but won't modify existing tables.
# for 1 time  AND remove in productions
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=APP_NAME,
    description=(
        "RAG Based Document "
        "Question Answering System"),
    version=APP_VERSION)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(chat_sessions_router)

@app.get("/")
def root():

    return {
        "message": "Document Q&A API is running",
        "version": APP_VERSION
    }

