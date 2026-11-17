"""Database queries and upserts for per-user email summaries."""
from datetime import datetime
from math import ceil
from uuid import uuid4
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from backend.database.models import EmailSummary


def upsert_summaries(db: Session, user_id: str, rows: list[dict]) -> int:
    for row in rows:
        received_at = datetime.fromisoformat(row["received_at"])
        record = db.scalar(
            select(EmailSummary).where(
                EmailSummary.user_id == user_id,
                EmailSummary.thread_id == row["thread_id"],
            )
        )
        if record is None:
            record = EmailSummary(
                id=str(uuid4()),
                user_id=user_id,
                thread_id=row["thread_id"],
                received_at=received_at,
                summary=row["summary"],
            )
            db.add(record)
        record.sender_name = row["sender_name"]
        record.sender_email = row["sender_email"]
        record.subject = row["subject"]
        record.received_at = received_at
        record.summary = row["summary"]
        if record.category_source != "manual":
            record.category = row["category"]
            record.category_source = "ai"
        record.priority = row["priority"]
        record.reply_decision = row["reply_decision"]
        record.reply_reason = row["reply_reason"]
        record.key_points = row.get("key_points", [])
        record.deadline = row.get("deadline")
        record.suggested_reply = row.get("suggested_reply")
    db.commit()
    return len(rows)


def list_summaries(
    db: Session,
    user_id: str,
    *,
    page: int,
    page_size: int,
    category: str | None = None,
    reply_decision: str | None = None,
    priority: str | None = None,
    search: str | None = None,
) -> tuple[list[EmailSummary], int, int]:
    query = select(EmailSummary).where(EmailSummary.user_id == user_id)
    if category:
        query = query.where(func.lower(EmailSummary.category) == category.lower())
    if reply_decision:
        query = query.where(EmailSummary.reply_decision == reply_decision)
    if priority:
        query = query.where(EmailSummary.priority == priority)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                EmailSummary.subject.ilike(pattern),
                EmailSummary.summary.ilike(pattern),
                EmailSummary.sender_name.ilike(pattern),
                EmailSummary.sender_email.ilike(pattern),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        db.scalars(
            query.order_by(EmailSummary.received_at.desc(), EmailSummary.thread_id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return items, total, ceil(total / page_size)


def get_summary(db: Session, user_id: str, thread_id: str) -> EmailSummary | None:
    return db.scalar(
        select(EmailSummary).where(
            EmailSummary.user_id == user_id,
            EmailSummary.thread_id == thread_id,
        )
    )


def set_category(db: Session, record: EmailSummary, category: str) -> EmailSummary:
    record.category = category
    record.category_source = "manual"
    db.commit()
    db.refresh(record)
    return record
