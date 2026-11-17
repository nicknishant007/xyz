"""Nodes for mailbox fetch, normalization, classification, validation, and persistence."""
import asyncio
import json
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agents.prompts import CLASSIFY_EMAIL_SYSTEM_PROMPT, REPAIR_OUTPUT_PROMPT
from backend.agents.schemas import EmailAnalysisBatch
from backend.agents.state import AnalysisState
from backend.agents.tool_registry import tool_registry
from backend.config.settings import settings
from backend.repositories.email_repository import get_summary, upsert_summaries
from backend.schemas.email import EmailAnalysis, ReplyDecision


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


def _get_structured_model(schema):
    from langchain_google_genai import ChatGoogleGenerativeAI

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required when mock integrations are disabled.")
    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0,
    )
    return model.with_structured_output(schema, method="json_schema")


async def classify_thread(thread: dict[str, Any], *, repair: bool = False) -> EmailAnalysis:
    if settings.mock_integrations:
        return _mock_analysis(thread)

    model = _get_structured_model(EmailAnalysis)
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
        return _enforce_analysis_rules(
            analysis,
            thread["thread_id"],
            latest_sender_is_user=thread.get("latest_sender_is_user", False),
        )
    except Exception:
        if not repair:
            return await classify_thread(thread, repair=True)
        return _review_fallback(thread["thread_id"])


async def _classify_batch(threads: list[dict[str, Any]]) -> list[EmailAnalysis]:
    if settings.mock_integrations:
        return [_mock_analysis(thread) for thread in threads]

    try:
        model = _get_structured_model(EmailAnalysisBatch)
    except Exception:
        return [_review_fallback(thread["thread_id"]) for thread in threads]
    expected_ids = [thread["thread_id"] for thread in threads]
    payload = [
        {
            "thread_id": thread["thread_id"],
            "subject": thread.get("subject", ""),
            "sender": thread.get("sender_email", ""),
            "messages": thread.get("messages", []),
        }
        for thread in threads
    ]
    try:
        result = await model.ainvoke([
            SystemMessage(content=CLASSIFY_EMAIL_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ])
        batch = EmailAnalysisBatch.model_validate(result)
    except Exception:
        return await _retry_batch_individually(threads)

    grouped: dict[str, list[EmailAnalysis]] = {}
    for analysis in batch.analyses:
        grouped.setdefault(analysis.thread_id, []).append(analysis)

    valid: dict[str, EmailAnalysis] = {}
    invalid_threads: list[dict[str, Any]] = []
    for thread in threads:
        thread_id = thread["thread_id"]
        candidates = grouped.get(thread_id, [])
        try:
            if len(candidates) != 1:
                raise ValueError("Expected exactly one analysis for this thread.")
            valid[thread_id] = _enforce_analysis_rules(
                candidates[0],
                thread_id,
                latest_sender_is_user=thread.get("latest_sender_is_user", False),
            )
        except Exception:
            invalid_threads.append(thread)

    if invalid_threads:
        repaired = await _retry_batch_individually(invalid_threads)
        valid.update({thread["thread_id"]: analysis for thread, analysis in zip(invalid_threads, repaired)})
    return [valid.get(thread_id, _review_fallback(thread_id)) for thread_id in expected_ids]


async def _retry_batch_individually(
    threads: list[dict[str, Any]],
) -> list[EmailAnalysis]:
    """Retry only conversations whose batch result was missing or invalid."""
    repaired: list[EmailAnalysis] = []
    for thread in threads:
        try:
            analysis = await classify_thread(thread, repair=True)
            repaired.append(
                _enforce_analysis_rules(
                    analysis,
                    thread["thread_id"],
                    latest_sender_is_user=thread.get("latest_sender_is_user", False),
                )
            )
        except Exception:
            repaired.append(_review_fallback(thread["thread_id"]))
    return repaired


def _enforce_analysis_rules(
    analysis: EmailAnalysis,
    expected_thread_id: str,
    *,
    latest_sender_is_user: bool = False,
) -> EmailAnalysis:
    if analysis.thread_id != expected_thread_id:
        raise ValueError("Analysis thread ID does not match the input.")
    if latest_sender_is_user:
        return analysis.model_copy(
            update={
                "reply_decision": ReplyDecision.no_reply,
                "reply_reason": "The latest message was sent by the user.",
                "suggested_reply": None,
            }
        )
    if analysis.reply_decision.value == "reply" and analysis.category.value != "Important":
        return analysis.model_copy(
            update={
                "reply_decision": ReplyDecision.review,
                "reply_reason": "Replies are allowed only for the Important category.",
                "suggested_reply": None,
            }
        )
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
    semaphore = asyncio.Semaphore(settings.agent_concurrency)

    async def fetch_one(row: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            try:
                return await tool_registry.ainvoke(
                    "get_gmail_thread", {"thread_id": row["thread_id"]}
                )
            except Exception:
                return row

    threads = await asyncio.gather(*(fetch_one(row) for row in rows))
    return {"raw_threads": threads}


async def normalize_threads_node(state: AnalysisState) -> dict[str, Any]:
    return {"normalized_threads": [normalize_thread(row) for row in state.get("raw_threads", [])]}


async def classify_threads_node(state: AnalysisState) -> dict[str, Any]:
    threads = state.get("normalized_threads", [])
    semaphore = asyncio.Semaphore(settings.agent_concurrency)
    batches = [threads[index:index + 5] for index in range(0, len(threads), 5)]

    async def classify_limited(batch: list[dict[str, Any]]) -> list[EmailAnalysis]:
        async with semaphore:
            return await _classify_batch(batch)

    results = await asyncio.gather(*(classify_limited(batch) for batch in batches))
    flattened = [analysis for batch in results for analysis in batch]
    serialized = [analysis.model_dump(mode="json") for analysis in flattened]
    failed = sum(analysis.summary.startswith("Automated analysis failed") for analysis in flattened)
    return {"analyses": serialized, "failed_count": failed}


async def validate_analyses_node(state: AnalysisState) -> dict[str, Any]:
    threads = state.get("normalized_threads", [])
    results = state.get("analyses", [])
    validated: list[dict[str, Any]] = []
    for index, thread in enumerate(threads):
        try:
            if index >= len(results):
                raise ValueError("Missing model result.")
            analysis = _enforce_analysis_rules(
                EmailAnalysis.model_validate(results[index]),
                thread["thread_id"],
                latest_sender_is_user=thread.get("latest_sender_is_user", False),
            )
        except Exception:
            try:
                analysis = await classify_thread(thread, repair=True)
            except Exception:
                analysis = _review_fallback(thread["thread_id"])
        validated.append(analysis.model_dump(mode="json"))
    failed = sum(
        analysis["summary"].startswith("Automated analysis failed")
        for analysis in validated
    )
    return {"analyses": validated, "failed_count": failed}


async def persist_analyses_node(state: AnalysisState) -> dict[str, Any]:
    threads = state.get("normalized_threads", [])
    analyses = state.get("analyses", [])
    rows: list[dict[str, Any]] = []
    for thread, analysis in zip(threads, analyses):
        rows.append({**thread, **analysis, "received_at": thread["received_at"]})
    db = state["db"]
    count = upsert_summaries(db, state["user_id"], rows) if rows else 0
    return {"persisted_count": count}

async def create_important_reply_drafts_node(state: AnalysisState) -> dict[str, Any]:
    """Create drafts only for persisted Important conversations approved for reply."""
    db = state["db"]
    user_id = state["user_id"]
    analyses = state.get("analyses", [])
    created = 0
    failed = 0
    for analysis in analyses:
        if analysis.get("reply_decision") != "reply" or not analysis.get("suggested_reply"):
            continue
        row = get_summary(db, user_id, analysis["thread_id"])
        if row is None or row.category != "Important" or row.reply_decision != "reply":
            continue
        try:
            result = await tool_registry.ainvoke(
                "create_important_reply_draft_tool",
                {
                    "user_id": user_id,
                    "thread_id": row.thread_id,
                    "body": analysis["suggested_reply"],
                },
            )
            created += int(bool(result.get("created")))
        except Exception:
            failed += 1
    return {"draft_created_count": created, "draft_failed_count": failed}
