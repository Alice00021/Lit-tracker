
from common import BaseSettings


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

    # Taste profile (LangGraph retry)
    TASTE_MAX_RETRIES: int = 3
    TASTE_RETRY_BACKOFF_SECONDS: float = 1.0

    # Taste profile (восстановление после рестарта)
    # Запись pending/processing без движения дольше этого времени считается зависшей.
    # Должно быть больше таймаута одного вызова LLM (180 с).
    TASTE_STALE_AFTER_SECONDS: int = 300
    TASTE_RECOVERY_INTERVAL_SECONDS: int = 60

    # Rate limit
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

settings = Settings()