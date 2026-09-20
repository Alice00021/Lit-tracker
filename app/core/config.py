from common import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки для Literary Tracker"""

    SERVICE_NAME: str = Field(default="lit-tracker", env="SERVICE_NAME")
    PORT: int = Field(default=8001, env="PORT")

    # Ollama
    EMBEDDING_PROVIDER: str = Field(default="ollama", env="EMBEDDING_PROVIDER")
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

    # OpenAI
    OPENAI_API_KEY: str = Field(default="sk-mock", env="OPENAI_API_KEY")
    OPENAI_EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        env="OPENAI_EMBEDDING_MODEL",
    )
    OPENAI_EMBEDDING_DIMENSION: int = Field(
        default=1536,
        env="OPENAI_EMBEDDING_DIMENSION",
    )
    OPENAI_LLM_MODEL: str = Field(
        default="gpt-4o-mini",
        env="OPENAI_LLM_MODEL",
    )
    OPENAI_TEMPERATURE: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    OPENAI_MAX_TOKENS: int = Field(default=1000, env="OPENAI_MAX_TOKENS")

settings = Settings()