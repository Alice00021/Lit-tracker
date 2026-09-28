from common import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    SERVICE_NAME: str = "lit-tracker"
    PORT: int = 8001

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_LLM_MODEL: str = "llama3.1"
    EMBEDDING_DIMENSION: int = 768

    # LangChain
    LANGCHAIN_TRACING_V2: bool = False

settings = Settings()