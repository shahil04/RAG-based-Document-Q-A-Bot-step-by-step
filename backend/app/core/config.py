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

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)