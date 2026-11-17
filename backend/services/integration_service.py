"""Provider boundary. Mock mode is deterministic and has no external side effects."""
from datetime import datetime, timezone
from uuid import uuid4
from backend.config.settings import settings


class IntegrationService:
    async def list_threads(self, query: str = "in:inbox newer_than:30d") -> list[dict]:
        if not settings.mock_integrations:
            raise RuntimeError("Live Gmail adapter is not implemented; enable mock mode.")
        now = datetime.now(timezone.utc)
        return [
            {
                "thread_id": "mock-thread-001",
                "sender_name": "Alex Morgan",
                "sender_email": "alex@example.test",
                "subject": "Project proposal review",
                "received_at": now.isoformat(),
                "summary": "Alex asks you to review the project proposal before Friday.",
                "category": "Work",
                "priority": "medium",
                "reply_decision": "reply",
                "reply_reason": "The sender requested feedback by Friday.",
                "key_points": ["Review the attached proposal", "Requested by Friday"],
                "deadline": "Friday",
                "suggested_reply": "Hi Alex, thanks for sharing the proposal. I’ll review it and send you my feedback.",
            },
            {
                "thread_id": "mock-thread-002",
                "sender_name": "Example Store",
                "sender_email": "receipts@example.test",
                "subject": "Your order receipt",
                "received_at": now.isoformat(),
                "summary": "Automated receipt for a recent order.",
                "category": "Receipts",
                "priority": "low",
                "reply_decision": "no_reply",
                "reply_reason": "This is an automated receipt with no response requested.",
                "key_points": ["Receipt notification"],
                "deadline": None,
                "suggested_reply": None,
            },
        ]

    async def create_draft(self, thread_id: str, body: str) -> dict:
        if not settings.mock_integrations:
            raise RuntimeError("Live Gmail adapter is not implemented; enable mock mode.")
        if not body.strip():
            raise ValueError("Draft body cannot be empty.")
        return {"draft_id": f"mock-draft-{uuid4().hex[:12]}", "thread_id": thread_id, "status": "draft"}

    async def send_draft(self, draft_id: str, confirmed: bool) -> dict:
        if not confirmed:
            raise ValueError("Explicit confirmation is required.")
        if not settings.mock_integrations:
            raise RuntimeError("Live Gmail sending is not implemented.")
        return {"draft_id": draft_id, "status": "sent", "simulated": True}


integration_service = IntegrationService()
