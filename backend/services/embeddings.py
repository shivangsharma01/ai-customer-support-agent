import httpx

from config import settings


def embed(texts: list[str]) -> list[list[float]]:
    """Embed texts via the OpenAI-compatible /v1/embeddings endpoint (Ollama or vLLM)."""
    resp = httpx.post(
        f"{settings.embedding_base_url}/embeddings",
        json={"model": settings.embedding_model, "input": texts},
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return [item["embedding"] for item in data]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
