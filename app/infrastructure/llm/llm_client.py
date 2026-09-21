import httpx
import json
from typing import Dict, Any, List
from app.core.config import settings
from app.infrastructure.llm.prompts import build_taste_prompt
from common import get_logger, ServiceError

logger = get_logger(__name__)


class LLMClient:
    """Клиент для работы с LLM через Ollama."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_LLM_MODEL
        logger.info(f"✅ LLMClient (Ollama): {self.model}")

    async def analyze_taste(self, notes: List[str]) -> Dict[str, Any]:
        """Проанализировать вкус пользователя по заметкам."""
        if not notes:
            return {
                "themes": [],
                "style": "",
                "loves": [],
                "dislikes": [],
                "summary": "Недостаточно данных для анализа",
            }

        prompt = build_taste_prompt(notes)

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                return json.loads(data["response"])

        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {e}")
            raise ServiceError(f"LLM returned invalid JSON: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise ServiceError(f"Failed to call Ollama: {str(e)}")