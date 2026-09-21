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


def build_taste_prompt(notes: list[str]) -> str:
    notes_text = "\n".join(f"- {n}" for n in notes)
    return TASTE_ANALYSIS_PROMPT.format(notes=notes_text)