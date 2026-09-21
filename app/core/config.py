from common import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки для Literary Tracker"""

    SERVICE_NAME: str = Field(default="lit-tracker", env="SERVICE_NAME")
    PORT: int = Field(default=8001, env="PORT")

    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        env="OLLAMA_BASE_URL",
    )
    OLLAMA_EMBEDDING_MODEL: str = Field(
        default="nomic-embed-text",
        env="OLLAMA_EMBEDDING_MODEL",
    )
    OLLAMA_LLM_MODEL: str = Field(
        default="llama3.1",
        env="OLLAMA_LLM_MODEL",
    )
    EMBEDDING_DIMENSION: int = Field(
        default=768,
        env="EMBEDDING_DIMENSION",
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6380/0",
        env="REDIS_URL",
    )
    CACHE_TTL_SECONDS: int = Field(
        default=300,
        env="CACHE_TTL_SECONDS",
    )


settings = Settings()