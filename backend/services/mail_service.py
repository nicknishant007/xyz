"""Mailbox business rules shared by API routes and agent tools."""
from sqlalchemy.orm import Session
from backend.repositories.email_repository import get_summary
from backend.services.integration_service import integration_service


async def create_important_reply_draft(
    db: Session,
    user_id: str,
    thread_id: str,
    body: str,
    *,
    reuse_existing: bool = True,
) -> dict:
    """Create a reply draft only for a user's Important conversation needing a reply."""
    row = get_summary(db, user_id, thread_id)
    if row is None:
        raise LookupError("Conversation not found.")
    if row.category != "Important":
        raise PermissionError("Reply drafts are allowed only for Important conversations.")
    if row.reply_decision != "reply":
        raise PermissionError("This conversation is not approved for a reply.")
    if not body or not body.strip():
        raise ValueError("Draft body cannot be empty.")
    if len(body) > 20000:
        raise ValueError("Draft body exceeds the 20000 character limit.")
    if row.draft_status == "sent":
        raise ValueError("This conversation already has a completed reply.")
    if reuse_existing and row.draft_status == "draft" and row.draft_id:
        return {
            "draft_id": row.draft_id,
            "thread_id": row.thread_id,
            "status": "draft",
            "created": False,
        }

    result = await integration_service.create_draft(row.thread_id, body)
    row.draft_id = result["draft_id"]
    row.draft_status = "draft"
    db.commit()
    return {**result, "created": True}
