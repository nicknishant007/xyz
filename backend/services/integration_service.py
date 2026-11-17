"""Provider boundary. Mock mode is deterministic and has no external side effects."""
from datetime import datetime, timezone
from uuid import uuid4
from backend.config.settings import settings


class IntegrationService:
    async def get_profile(self) -> dict:
        """Return safe mock metadata for the connected mailbox."""
        if not settings.mock_integrations:
            raise RuntimeError("Live Gmail adapter is not implemented; enable mock mode.")
        return {
            "email_address": "demo@example.test",
            "messages_total": 3,
            "threads_total": 2,
            "history_id": "mock-history-001",
        }

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

    async def get_thread(self, thread_id: str) -> dict:
        rows = await self.list_threads()
        for row in rows:
            if row["thread_id"] == thread_id:
                latest_at = row["received_at"]
                messages = [
                    {
                        "message_id": f"{thread_id}-message-001",
                        "sender_name": row["sender_name"],
                        "sender_email": row["sender_email"],
                        "timestamp": latest_at,
                        "body_text": row["summary"],
                        "is_user": False,
                    }
                ]
                if thread_id == "mock-thread-001":
                    messages.insert(
                        0,
                        {
                            "message_id": f"{thread_id}-message-000",
                            "sender_name": "Demo User",
                            "sender_email": "demo@example.test",
                            "timestamp": latest_at,
                            "body_text": "Thanks for sending this over. I will take a look.",
                            "is_user": True,
                        },
                    )
                return {**row, "messages": messages}
        raise ValueError("Conversation not found.")

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
