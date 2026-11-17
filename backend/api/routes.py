"""Authenticated, database-backed mailbox endpoints."""
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.api.dependencies import get_current_user
from backend.api.security import require_csrf
from backend.agents.tool_registry import tool_registry
from backend.agents.chat_graph import run_chat_agent
from backend.database.models import EmailSummary, SyncRun, User
from backend.database.session import get_db
from backend.services.sync_service import execute_sync_job
from backend.repositories.email_repository import (
    get_summary,
    list_summaries,
    set_category,
)
from backend.services.integration_service import integration_service
from backend.services.mail_service import create_important_reply_draft
from backend.schemas.agent import AgentChatRequest, AgentChatResponse
from backend.schemas.email import (
    CategoryUpdate,
    DraftRequest,
    EmailDetail,
    EmailItem,
    EmailPage,
    SendRequest,
    SyncStatus,
)

router = APIRouter()


def _as_item(row: EmailSummary) -> EmailItem:
    return EmailItem(
        id=row.thread_id,
        thread_id=row.thread_id,
        sender_name=row.sender_name,
        sender_email=row.sender_email,
        subject=row.subject,
        received_at=row.received_at,
        summary=row.summary,
        category=row.category,
        priority=row.priority,
        reply_decision=row.reply_decision,
        reply_reason=row.reply_reason,
        key_points=row.key_points or [],
        deadline=row.deadline,
        suggested_reply=row.suggested_reply,
        draft_status=row.draft_status,
        draft_id=row.draft_id,
    )


@router.get("/emails", response_model=EmailPage)
def list_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    category: str | None = None,
    reply_decision: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows, total, total_pages = list_summaries(
        db,
        user.id,
        page=page,
        page_size=page_size,
        category=category,
        reply_decision=reply_decision,
        priority=priority,
        search=search,
    )
    return EmailPage(
        items=[_as_item(row) for row in rows],
        pagination={"page": page, "page_size": page_size, "total": total, "total_pages": total_pages},
    )


@router.get("/emails/{email_id}", response_model=EmailDetail)
async def get_email(
    email_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_summary(db, user.id, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        thread = await integration_service.get_thread(email_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=502, detail="Could not retrieve conversation messages.") from exc
    item = _as_item(row).model_dump()
    return EmailDetail.model_validate({**item, "messages": thread.get("messages", [])})


@router.patch("/emails/{email_id}/category", response_model=EmailItem)
def update_category(
    email_id: str,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    csrf_token: str = Depends(require_csrf),
):
    row = get_summary(db, user.id, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _as_item(set_category(db, row, payload.category.value))


@router.post("/sync", response_model=SyncStatus, status_code=202)
def sync_mailbox(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    csrf_token: str = Depends(require_csrf),
):
    running = db.scalar(
        select(SyncRun).where(
            SyncRun.user_id == user.id,
            SyncRun.status.in_(("queued", "running")),
        )
    )
    if running is not None:
        raise HTTPException(
            status_code=409,
            detail={"message": "A mailbox sync is already running.", "job_id": running.id},
        )
    run = SyncRun(id=uuid4().hex, user_id=user.id, status="queued")
    db.add(run)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        running = db.scalar(
            select(SyncRun).where(
                SyncRun.user_id == user.id,
                SyncRun.status.in_(("queued", "running")),
            )
        )
        raise HTTPException(
            status_code=409,
            detail={"message": "A mailbox sync is already running.", "job_id": running.id if running else None},
        ) from exc
    background_tasks.add_task(execute_sync_job, user.id, run.id)
    return SyncStatus(
        job_id=run.id,
        status=run.status,
        processed=run.processed,
        failed=run.failed,
    )

@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(
    payload: AgentChatRequest,
    user: User = Depends(get_current_user),
    csrf_token: str = Depends(require_csrf),
):
    """Run one bounded Gemini request that may call allowlisted mailbox tools."""
    result = await run_chat_agent(user.id, payload.message)
    return AgentChatResponse.model_validate(result)


@router.get("/agent/tools")
def list_agent_tools(
    user: User = Depends(get_current_user),
):
    """Return the names, descriptions, schemas, and side-effect classes of allowed agent tools."""
    return [asdict(description) for description in tool_registry.list_descriptions()]


@router.get("/sync/status", response_model=SyncStatus)
def sync_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    run = db.scalar(
        select(SyncRun)
        .where(SyncRun.user_id == user.id)
        .order_by(SyncRun.started_at.desc(), SyncRun.id.desc())
        .limit(1)
    )
    if run is None:
        return SyncStatus(job_id="none", status="idle")
    return SyncStatus(
        job_id=run.id,
        status=run.status,
        processed=run.processed,
        failed=run.failed,
        last_successful_sync=run.finished_at if run.status == "completed" else None,
    )


@router.post("/emails/{email_id}/draft")
async def create_draft(
    email_id: str,
    payload: DraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    csrf_token: str = Depends(require_csrf),
):
    row = get_summary(db, user.id, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    body = payload.body if payload.body is not None else row.suggested_reply
    if not body or not body.strip():
        raise HTTPException(status_code=422, detail="A non-empty reply body is required.")
    try:
        return await create_important_reply_draft(
            db, user.id, row.thread_id, body, reuse_existing=False
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found.") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Draft provider is unavailable.") from exc


@router.post("/emails/{email_id}/send")
async def send_draft(
    email_id: str,
    payload: SendRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    csrf_token: str = Depends(require_csrf),
):
    row = get_summary(db, user.id, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if row.category != "Important" or row.reply_decision != "reply":
        raise HTTPException(
            status_code=403,
            detail="Replies are allowed only for Important conversations approved for reply.",
        )
    if not payload.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required.")
    if row.draft_status != "draft" or not row.draft_id:
        raise HTTPException(status_code=409, detail="Create a Gmail draft before sending.")
    if payload.draft_id and payload.draft_id != row.draft_id:
        raise HTTPException(status_code=404, detail="Draft does not belong to this conversation.")
    try:
        result = await integration_service.send_draft(row.draft_id, payload.confirmed)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row.draft_status = "sent"
    db.commit()
    return result
