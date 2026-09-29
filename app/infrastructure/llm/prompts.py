"""Промпты для LLM."""

TASTE_ANALYSIS_PROMPT = """Проанализируй читательский вкус по заметкам.

Заметки:
{notes}

Верни ТОЛЬКО JSON:
{{
  "themes": ["тема1", "тема2"],
  "style": "описание стиля",
  "loves": ["что нравится"],
  "dislikes": ["что не нравится"],
  "summary": "краткое описание"
}}
"""


RETRY_FEEDBACK_TEMPLATE = """
ВАЖНО: предыдущий ответ не подошёл: {feedback}.
Верни ВАЛИДНЫЙ JSON со ВСЕМИ полями themes, style, loves, dislikes, summary.
Поля themes, style и summary не должны быть пустыми.
"""


def build_taste_prompt(notes: list[str], feedback: str | None = None) -> str:
    """Собрать промпт. Если это повторная попытка — добавляем, что было не так."""
    notes_text = "\n".join(f"- {n}" for n in notes)
    prompt = TASTE_ANALYSIS_PROMPT.format(notes=notes_text)
    if feedback:
        prompt += RETRY_FEEDBACK_TEMPLATE.format(feedback=feedback)
    return prompt


# SMART SEARCH AGENT

SMART_SEARCH_SYSTEM_PROMPT = """Ты — умный помощник по подбору книг.

Твоя задача — помочь пользователю найти книги по его запросу.

У тебя есть инструменты:
- search_similar_books: семантический поиск по описанию (темы, настроение)
- filter_books_by_author: поиск по автору
- get_all_books: все книги (если ничего не подходит)

Как работать:
1. Проанализируй запрос пользователя
2. Выбери подходящие tools
3. Вызови их (можно несколько)
4. Объясни, почему эти книги подходят

ВАЖНО:
- Если пользователь описывает НАСТРОЕНИЕ или ТЕМУ — используй search_similar_books
- Если упоминает АВТОРА — используй filter_books_by_author
- Если нужен общий обзор — используй get_all_books
- Можешь комбинировать tools

Отвечай на русском языке.
"""