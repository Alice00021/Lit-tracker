import json
from openai import AsyncOpenAI
from typing import Dict, Any, List
from app.core.config import settings
from common import get_logger, ServiceError

logger = get_logger(__name__)


class LLMClient:
    """
    Клиент для работы с LLM (GPT) — анализ вкуса, рекомендации.
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_LLM_MODEL
        self.temperature = settings.OPENAI_TEMPERATURE
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        logger.info(f"✅ LLMClient: {self.model}")

    async def analyze_taste(self, notes: List[str]) -> Dict[str, Any]:
        """
        Проанализировать вкус пользователя по заметкам.

        Returns:
            {
                "themes": ["тема1", ...],
                "style": "описание стиля",
                "loves": ["что нравится", ...],
                "dislikes": ["что не нравится", ...],
                "summary": "краткое описание"
            }
        """
        if not notes:
            return {
                "themes": [],
                "style": "",
                "loves": [],
                "dislikes": [],
                "summary": "Недостаточно данных для анализа",
            }

        prompt = f"""Ты — литературный критик и психолог. Проанализируй читательский вкус по заметкам о книгах.

Заметки пользователя:
{chr(10).join(f"- {note}" for note in notes)}

Верни ТОЛЬКО JSON без markdown:
{{
  "themes": ["тема1", "тема2", "тема3"],
  "style": "описание литературного стиля, который нравится",
  "loves": ["что нравится1", "что нравится2"],
  "dislikes": ["что не нравится1"],
  "summary": "краткое описание вкуса (2-3 предложения)"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты аналитик литературы. Отвечай только JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            logger.error(f"LLM error: {e}")
            raise ServiceError(f"Failed to analyze taste: {str(e)}")