from common import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки для Literary Tracker"""

    SERVICE_NAME: str = Field(default="lit-tracker", env="SERVICE_NAME")
    PORT: int = Field(default=8001, env="PORT")

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


settings = Settings()