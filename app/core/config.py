from common import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки для Literary Tracker"""

    SERVICE_NAME: str = Field(default="lit-tracker", env="SERVICE_NAME")
    PORT: int = Field(default=8001, env="PORT")

    EMBEDDING_MODEL: str = Field(
        default="all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    EMBEDDING_DIMENSION: int = Field(
        default=384,
        env="EMBEDDING_DIMENSION"
    )


settings = Settings()