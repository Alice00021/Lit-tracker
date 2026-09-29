from typing import Optional, TypedDict


class TasteProfileState(TypedDict):
    """Состояние графа."""

    # Входные данные
    user_id: int

    # Промежуточные
    notes: list[str]
    analysis: Optional[dict]
    error: Optional[str]
    retryable: bool     # False — повтор не поможет (например, нет заметок)
    feedback: Optional[str]  # что не так с прошлой попыткой — уходит в промпт
    retry_count: int
    max_retries: int

    # Выходные
    status: str         # pending / processing / done / failed
    entries_count: int