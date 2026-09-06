from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

from app.core.config import (
    GROQ_API_KEY,
    OPENAI_API_KEY,
    GOOGLE_API_KEY,
    ANTHROPIC_API_KEY,
)


def create_groq(model: str, temperature: float):
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not configured"
        )

    return ChatGroq(
        model=model,
        api_key=GROQ_API_KEY,
        temperature=temperature,
    )


def create_openai(model: str, temperature: float):
    if not OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is not configured"
        )

    return ChatOpenAI(
        model=model,
        api_key=OPENAI_API_KEY,
        temperature=temperature,
    )


def create_gemini(model: str, temperature: float):
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY or GEMINI_API_KEY is not configured"
        )

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=GOOGLE_API_KEY,
        temperature=temperature,
    )


def create_anthropic(model: str, temperature: float):
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY is not configured"
        )

    return ChatAnthropic(
        model=model,
        api_key=ANTHROPIC_API_KEY,
        temperature=temperature,
    )