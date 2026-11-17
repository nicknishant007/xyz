"""Nodes for mailbox fetch, normalization, classification, validation, and persistence."""
import asyncio
import json
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.prompts import CLASSIFY_EMAIL_SYSTEM_PROMPT, REPAIR_OUTPUT_PROMPT
from backend.agents.state import AnalysisState
from backend.agents.tool_registry import tool_registry
from backend.config.settings import settings
from backend.repositories.email_repository import upsert_summaries
from backend.schemas.email import EmailAnalysis


def normalize_thread(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a provider thread to a compact, consistently shaped message list."""
    messages = row.get("messages") or [
        {
            "message_id": f'{row["thread_id"]}-latest',
            "sender_name": row.get("sender_name", ""),
            "sender_email": row.get("sender_email", ""),
            "timestamp": row.get("received_at", ""),
            "body_text": row.get("body_text") or row.get("summary", ""),
        }
    ]
    ordered = sorted(messages, key=lambda item: item.get("timestamp", ""))
    latest = ordered[-1] if ordered else {}
    return {
        **row,
        "messages": ordered,
        "latest_message": latest,
        "latest_sender_is_user": bool(latest.get("is_user", False)),
        "body_text": "\n\n".join(
            str(message.get("body_text", "")) for message in ordered if message.get("body_text")
        ),
    }


def _mock_analysis(thread: dict[str, Any]) -> EmailAnalysis:
    """Use deterministic fake analysis while all integrations are in mock mode."""
    return EmailAnalysis(
        thread_id=thread["thread_id"],
        summary=thread.get("summary") or "Conversation requires review.",
        category=thread.get("category", "Other"),
        priority=thread.get("priority", "medium"),
        reply_decision=thread.get("reply_decision", "review"),
        reply_reason=thread.get("reply_reason", "Mock analysis data."),
        key_points=thread.get("key_points", []),
        deadline=thread.get("deadline"),
        suggested_reply=thread.get("suggested_reply"),
    )


def _get_structured_model():
    from langchain_google_genai import ChatGoogleGenerativeAI

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required when mock integrations are disabled.")
    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0,
    )
    return model.with_structured_output(EmailAnalysis, method="json_schema")


async def classify_thread(thread: dict[str, Any], *, repair: bool = False) -> EmailAnalysis:
    if settings.mock_integrations:
        return _mock_analysis(thread)

    model = _get_structured_model()
    system_prompt = CLASSIFY_EMAIL_SYSTEM_PROMPT
    if repair:
        system_prompt += "\n" + REPAIR_OUTPUT_PROMPT
    payload = {
        "thread_id": thread["thread_id"],
        "subject": thread.get("subject", ""),
        "sender": thread.get("sender_email", ""),
        "messages": thread.get("messages", []),
    }
    try:
        result = await model.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ])
        analysis = EmailAnalysis.model_validate(result)
        return _enforce_analysis_rules(analysis, thread["thread_id"])
    except Exception:
        if not repair:
            return await classify_thread(thread, repair=True)
        return _review_fallback(thread["thread_id"])


def _enforce_analysis_rules(analysis: EmailAnalysis, expected_thread_id: str) -> EmailAnalysis:
    if analysis.thread_id != expected_thread_id:
        raise ValueError("Analysis thread ID does not match the input.")
    if analysis.reply_decision.value == "reply" and not (analysis.suggested_reply or "").strip():
        raise ValueError("A reply decision requires a non-empty suggested reply.")
    if analysis.reply_decision.value != "reply" and analysis.suggested_reply:
        analysis = analysis.model_copy(update={"suggested_reply": None})
    return analysis


def _review_fallback(thread_id: str) -> EmailAnalysis:
    return EmailAnalysis(
        thread_id=thread_id,
        summary="Automated analysis failed; please review this conversation.",
        category="Other",
        priority="medium",
        reply_decision="review",
        reply_reason="The conversation could not be validated safely.",
        key_points=[],
        suggested_reply=None,
    )


async def fetch_threads_node(state: AnalysisState) -> dict[str, Any]:
    rows = await tool_registry.ainvoke(
        "list_gmail_threads",
        {"query": "in:inbox newer_than:30d", "limit": settings.sync_max_threads},
    )
    return {"raw_threads": rows}


async def normalize_threads_node(state: AnalysisState) -> dict[str, Any]:
    return {"normalized_threads": [normalize_thread(row) for row in state.get("raw_threads", [])]}


async def classify_threads_node(state: AnalysisState) -> dict[str, Any]:
    semaphore = asyncio.Semaphore(settings.agent_concurrency)

    async def classify_limited(thread: dict[str, Any]) -> EmailAnalysis:
        async with semaphore:
            return await classify_thread(thread)

    analyses = await asyncio.gather(
        *(classify_limited(thread) for thread in state.get("normalized_threads", [])),
        return_exceptions=True,
    )
    output: list[dict[str, Any]] = []
    for thread, result in zip(state.get("normalized_threads", []), analyses):
        if isinstance(result, Exception):
            output.append(_review_fallback(thread["thread_id"]).model_dump(mode="json"))
        else:
            output.append(result.model_dump(mode="json"))
    return {"analyses": output}


async def validate_analyses_node(state: AnalysisState) -> dict[str, Any]:
    threads = state.get("normalized_threads", [])
    results = state.get("analyses", [])
    validated: list[dict[str, Any]] = []
    for thread, result in zip(threads, results):
        try:
            analysis = _enforce_analysis_rules(
                EmailAnalysis.model_validate(result),
                thread["thread_id"],
            )
        except Exception:
            try:
                analysis = await classify_thread(thread, repair=True)
            except Exception:
                analysis = _review_fallback(thread["thread_id"])
        validated.append(analysis.model_dump(mode="json"))
    return {"analyses": validated}


async def persist_analyses_node(state: AnalysisState) -> dict[str, Any]:
    threads = state.get("normalized_threads", [])
    analyses = state.get("analyses", [])
    rows: list[dict[str, Any]] = []
    for thread, analysis in zip(threads, analyses):
        rows.append(
            {
                **thread,
                **analysis,
                "received_at": thread["received_at"],
            }
        )
    db = state["db"]
    count = upsert_summaries(db, state["user_id"], rows) if rows else 0
    return {"persisted_count": count}
