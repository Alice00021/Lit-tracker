from langgraph.graph import END, StateGraph

from app.infrastructure.llm.langgraph.nodes import (
    analyze_taste,
    collect_notes,
    fail_profile,
    retry_analysis,
    save_profile,
    validate_analysis,
)
from app.infrastructure.llm.langgraph.state import TasteProfileState


def should_retry(state: TasteProfileState) -> str:
    """
    Условный переход после validate_analysis.

    Returns:
        - "save" — если валидно
        - "retry" — если есть ошибка и попытки остались
        - "fail" — если попытки кончились или повтор бессмыслен
    """
    if state.get("error") is None:
        return "save"

    if not state.get("retryable", True):
        return "fail"

    if state["retry_count"] >= state["max_retries"]:
        return "fail"

    return "retry"


def build_taste_profile_graph(checkpointer=None):
    """
    Собрать граф.

    checkpointer — если передан, состояние сохраняется после каждого узла,
    и упавший/прерванный запуск можно продолжить с последнего шага.
    """
    graph = StateGraph(TasteProfileState)

    # Добавляем узлы
    graph.add_node("collect_notes", collect_notes)
    graph.add_node("analyze_taste", analyze_taste)
    graph.add_node("validate_analysis", validate_analysis)
    graph.add_node("retry_analysis", retry_analysis)
    graph.add_node("save_profile", save_profile)
    graph.add_node("fail_profile", fail_profile)

    # Стартовый узел
    graph.set_entry_point("collect_notes")

    # Рёбра
    graph.add_edge("collect_notes", "analyze_taste")
    graph.add_edge("analyze_taste", "validate_analysis")

    # Условный переход
    graph.add_conditional_edges(
        "validate_analysis",
        should_retry,
        {
            "save": "save_profile",
            "retry": "retry_analysis",
            "fail": "fail_profile",
        },
    )

    graph.add_edge("retry_analysis", "analyze_taste")  # цикл
    graph.add_edge("save_profile", END)
    graph.add_edge("fail_profile", END)

    return graph.compile(checkpointer=checkpointer)

taste_profile_graph = build_taste_profile_graph()