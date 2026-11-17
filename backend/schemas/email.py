"""Validated API models for mailbox records and analysis."""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Category(str, Enum):
    work = "Work"
    personal = "Personal"
    finance = "Finance"
    receipts = "Receipts"
    travel = "Travel"
    promotions = "Promotions"
    social = "Social"
    updates = "Updates"
    other = "Other"


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class ReplyDecision(str, Enum):
    reply = "reply"
    no_reply = "no_reply"
    review = "review"


class EmailAnalysis(BaseModel):
    thread_id: str
    summary: str = Field(min_length=1)
    category: Category
    priority: Priority
    reply_decision: ReplyDecision
    reply_reason: str
    key_points: list[str] = Field(default_factory=list)
    deadline: str | None = None
    suggested_reply: str | None = None


class EmailItem(EmailAnalysis):
    id: str
    sender_name: str
    sender_email: str
    subject: str
    received_at: datetime
    draft_status: str = "none"
    draft_id: str | None = None


class EmailPage(BaseModel):
    items: list[EmailItem]
    pagination: dict[str, int]


class SyncStatus(BaseModel):
    job_id: str
    status: str
    processed: int = 0
    failed: int = 0
    last_successful_sync: datetime | None = None


class CategoryUpdate(BaseModel):
    category: Category


class DraftRequest(BaseModel):
    body: str | None = Field(default=None, max_length=20000)


class SendRequest(BaseModel):
    draft_id: str | None = None
    confirmed: bool = False
