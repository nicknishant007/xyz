"""Typed state shared by the deterministic LangGraph workflow."""
from typing import Any, TypedDict


class AnalysisState(TypedDict, total=False):
    user_id: str
    db: Any
    raw_threads: list[dict[str, Any]]
    normalized_threads: list[dict[str, Any]]
    analyses: list[dict[str, Any]]
    persisted_count: int
    error: str | None
