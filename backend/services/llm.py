from langchain_openai import ChatOpenAI

from config import settings


def get_llm(temperature: float = 0.1) -> ChatOpenAI:
    """Chat model over an OpenAI-compatible API (Ollama locally, vLLM in production)."""
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=temperature,
    )
