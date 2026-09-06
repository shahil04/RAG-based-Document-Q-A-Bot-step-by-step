from app.core.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
)

from app.llm.providers import (
    create_groq,
    create_openai,
    create_gemini,
    create_anthropic,
)


PROVIDERS = {
    "groq": create_groq,
    "openai": create_openai,
    "gemini": create_gemini,
    "anthropic": create_anthropic,
}


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
):

    provider = (
        provider or DEFAULT_LLM_PROVIDER
    ).lower()

    model = (
        model or DEFAULT_LLM_MODEL
    )

    if provider not in PROVIDERS:

        available = ", ".join(
            PROVIDERS.keys()
        )

        raise ValueError(
            f"Unsupported LLM provider: "
            f"{provider}. "
            f"Available providers: {available}"
        )

    llm_creator = PROVIDERS[provider]

    return llm_creator(
        model=model,
        temperature=temperature
    )