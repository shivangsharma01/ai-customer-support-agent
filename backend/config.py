from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/refund_agent"

    # OpenAI-compatible endpoint: Ollama locally, vLLM in production.
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen2.5:3b"
    llm_api_key: str = "not-needed"  # vLLM/Ollama ignore it; set for OpenAI

    embedding_base_url: str = "http://localhost:11434/v1"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # Voice (OpenAI Realtime API) — key lives in .env, never in source.
    openai_api_key: str = ""
    realtime_model: str = "gpt-realtime-2.1"

    # LangFuse — keys live in .env, never in source.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://us.cloud.langfuse.com"

    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
