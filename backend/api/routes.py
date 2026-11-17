"""HTTP routes for the initial mock-backed dashboard API."""
from math import ceil
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Query
from backend.schemas.email import EmailItem, EmailPage, SyncStatus
from backend.services.integration_service import integration_service

router = APIRouter()
_last_sync: SyncStatus | None = None


def _as_item(row: dict) -> EmailItem:
    from datetime import datetime
    return EmailItem(
        id=row["thread_id"],
        thread_id=row["thread_id"],
        sender_name=row["sender_name"],
        sender_email=row["sender_email"],
        subject=row["subject"],
        received_at=datetime.fromisoformat(row["received_at"]),
        summary=row["summary"],
        category=row["category"],
        priority=row["priority"],
        reply_decision=row["reply_decision"],
        reply_reason=row["reply_reason"],
        key_points=row["key_points"],
        deadline=row["deadline"],
        suggested_reply=row["suggested_reply"],
    )


@router.get("/emails", response_model=EmailPage)
async def list_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    category: str | None = None,
    reply_decision: str | None = None,
    priority: str | None = None,
    search: str | None = None,
):
    rows = await integration_service.list_threads()
    if category:
        rows = [r for r in rows if r["category"].lower() == category.lower()]
    if reply_decision:
        rows = [r for r in rows if r["reply_decision"] == reply_decision]
    if priority:
        rows = [r for r in rows if r["priority"] == priority]
    if search:
        term = search.casefold()
        rows = [r for r in rows if term in (r["subject"] + r["summary"] + r["sender_name"]).casefold()]
    total = len(rows)
    start = (page - 1) * page_size
    return EmailPage(
        items=[_as_item(r) for r in rows[start:start + page_size]],
        pagination={"page": page, "page_size": page_size, "total": total, "total_pages": ceil(total / page_size)},
    )


@router.get("/emails/{email_id}", response_model=EmailItem)
async def get_email(email_id: str):
    for row in await integration_service.list_threads():
        if row["thread_id"] == email_id:
            return _as_item(row)
    raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/sync", response_model=SyncStatus)
async def sync_mailbox():
    global _last_sync
    rows = await integration_service.list_threads()
    _last_sync = SyncStatus(job_id=uuid4().hex, status="completed", processed=len(rows), failed=0)
    return _last_sync


@router.get("/sync/status", response_model=SyncStatus)
async def sync_status():
    if _last_sync is None:
        return SyncStatus(job_id="none", status="idle")
    return _last_sync


@router.post("/emails/{email_id}/draft")
async def create_draft(email_id: str, body: str = Query(..., min_length=1)):
    try:
        return await integration_service.create_draft(email_id, body)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/emails/{email_id}/send")
async def send_draft(email_id: str, draft_id: str = Query(...), confirmed: bool = Query(False)):
    try:
        return await integration_service.send_draft(draft_id, confirmed)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
