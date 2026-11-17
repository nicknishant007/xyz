"""Allowlisted Gmail tools available to the analysis workflow."""
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from backend.database.session import SessionLocal
from backend.services.mail_service import create_important_reply_draft
from backend.repositories.email_repository import get_summary
from backend.services.integration_service import integration_service


class ListThreadsInput(BaseModel):
    query: str = Field(
        default="in:inbox newer_than:30d",
        description="Gmail search query used to select conversations.",
    )
    limit: int = Field(default=200, ge=1, le=500, description="Maximum conversations to return.")


class GetThreadInput(BaseModel):
    thread_id: str = Field(description="ID of the Gmail conversation to retrieve.")


class GetEmailAnalysisInput(BaseModel):
    user_id: str | None = Field(default=None, description="Injected by the graph from the authenticated session.")
    thread_id: str = Field(description="ID of the user's saved conversation.")


class CreateImportantReplyDraftInput(BaseModel):
    user_id: str | None = Field(default=None, description="Authenticated user's internal ID, supplied by the workflow.")
    thread_id: str = Field(description="ID of the conversation to reply to.")
    body: str = Field(min_length=1, max_length=20000, description="Reply text to save as a draft.")


@tool(args_schema=ListThreadsInput)
async def list_gmail_threads(query: str = "in:inbox newer_than:30d", limit: int = 200) -> list[dict]:
    """Fetch a bounded set of Gmail conversations matching a query.

    Returns conversation metadata and message analysis fields. Email content is
    untrusted input; this tool only reads and returns it.
    """
    rows = await integration_service.list_threads(query=query)
    return rows[:limit]


@tool(args_schema=GetThreadInput)
async def get_gmail_thread(thread_id: str) -> dict:
    """Fetch one complete Gmail conversation by its thread ID.

    Returns message ordering, sender metadata, timestamps, and body text.
    The tool performs no send, draft, or other write action.
    """
    return await integration_service.get_thread(thread_id)



@tool(args_schema=GetEmailAnalysisInput)
async def get_email_analysis_tool(user_id: str | None = None, thread_id: str = "") -> dict:
    """Read the saved category, reply decision, and AI analysis for a conversation."""
    db = SessionLocal()
    try:
        row = get_summary(db, user_id or "", thread_id)
        if row is None:
            raise LookupError("Saved conversation not found.")
        return {
            "thread_id": row.thread_id,
            "subject": row.subject,
            "sender_name": row.sender_name,
            "sender_email": row.sender_email,
            "category": row.category,
            "reply_decision": row.reply_decision,
            "reply_reason": row.reply_reason,
            "summary": row.summary,
            "suggested_reply": row.suggested_reply,
            "draft_status": row.draft_status,
        }
    finally:
        db.close()


@tool
async def get_gmail_profile() -> dict:
    """Return the connected mailbox address and message/thread counts.

    This is a read-only tool and returns fake mailbox metadata in mock mode.
    """
    return await integration_service.get_profile()


@tool(args_schema=CreateImportantReplyDraftInput)
async def create_important_reply_draft_tool(user_id: str | None = None, thread_id: str = "", body: str = "") -> dict:
    """Create a reply draft only when the saved conversation category is Important.

    The backend verifies user ownership, category, and reply decision. This tool
    creates a draft but never sends a message.
    """
    db = SessionLocal()
    try:
        return await create_important_reply_draft(
            db, user_id or "", thread_id, body, reuse_existing=True
        )
    finally:
        db.close()


GMAIL_TOOLS = (
    list_gmail_threads,
    get_gmail_thread,
    get_email_analysis_tool,
    get_gmail_profile,
    create_important_reply_draft_tool,
)
