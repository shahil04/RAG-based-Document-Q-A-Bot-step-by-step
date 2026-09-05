from fastapi import FastAPI

app = FastAPI(
    title="Document Q&A API",
    description="RAG Based Document Question Answering System",
    version="1.0.0",
)
# add for health checker for api
from api.health import router as health_router
app.include_router(health_router)


@app.get("/")
def root():
    return { "message": "Hello from Fastapi backend"}

