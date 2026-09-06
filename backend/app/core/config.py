import os

from dotenv import load_dotenv


load_dotenv()


APP_NAME = os.getenv(
    "APP_NAME",
    "Document Q&A API"
)

APP_VERSION = os.getenv(
    "APP_VERSION",
    "1.0.0"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY"
)

JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60"
    )
)

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

HF_TOKEN = os.getenv(
    "HF_TOKEN"
)

PINECONE_API_KEY = os.getenv(
    "PINECONE_API_KEY"
)

PINECONE_INDEX_NAME = os.getenv(
    "PINECONE_INDEX_NAME",
    "document-qa"
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv(
    "GOOGLE_API_KEY"
) or os.getenv(
    "GEMINI_API_KEY"
)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEFAULT_LLM_PROVIDER = os.getenv(
    "DEFAULT_LLM_PROVIDER",
    "groq"
)
DEFAULT_LLM_MODEL = os.getenv(
    "DEFAULT_LLM_MODEL",
    "qwen/qwen3.8-27b"
)   