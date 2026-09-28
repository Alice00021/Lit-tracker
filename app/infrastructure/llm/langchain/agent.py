"""
LangChain agent для умного поиска книг.

Использует LangChain 1.x API (create_agent).
"""
from langchain_ollama import ChatOllama
from langchain.agents import create_agent

from app.core.config import settings
from app.infrastructure.llm.langchain.tools import ALL_TOOLS
from app.infrastructure.llm.prompts import SMART_SEARCH_SYSTEM_PROMPT
from common import get_logger

logger = get_logger(__name__)

class SmartSearchAgent:
    """LangChain agent для умного поиска книг."""

    def __init__(self):
        # LLM через Ollama
        self.llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_LLM_MODEL,
            temperature=0.3,  # низкая — для точности
        )

        # Agent (LangChain 1.x)
        self.agent = create_agent(
            model=self.llm,
            tools=ALL_TOOLS,
            system_prompt=SMART_SEARCH_SYSTEM_PROMPT,
        )

    async def search(self, query: str) -> dict:
        """
        Выполнить умный поиск.

        Returns:
            {
                "query": str,
                "answer": str,
            }
        """
        logger.info(f"Smart search: {query}")

        try:
            result = await self.agent.ainvoke({
                "messages": [{"role": "user", "content": query}],
            })

            # Достаём финальный ответ
            messages = result.get("messages", [])
            answer = "Не удалось получить ответ"

            if messages:
                last_message = messages[-1]
                # content может быть строкой или списком блоков
                content = getattr(last_message, "content", None)
                if isinstance(content, str):
                    answer = content
                elif isinstance(content, list):
                    # Собираем текстовые блоки
                    texts = [
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    ]
                    answer = "\n".join(texts) or answer

            return {
                "query": query,
                "answer": answer,
            }

        except Exception as e:
            logger.error(f"Smart search failed: {e}", exc_info=True)
            return {
                "query": query,
                "answer": f"Ошибка поиска: {str(e)}",
            }


smart_search_agent = SmartSearchAgent()