"""Regression checks for the Important-only reply workflow."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from backend.agents.nodes import _enforce_analysis_rules
from backend.agents.tool_registry import tool_registry
from backend.schemas.email import EmailAnalysis, ReplyDecision
from backend.services.mail_service import create_important_reply_draft


def analysis(category: str, decision: str = "reply") -> EmailAnalysis:
    return EmailAnalysis(
        thread_id="thread-1",
        summary="Please review and reply.",
        category=category,
        priority="high",
        reply_decision=decision,
        reply_reason="A response was requested.",
        suggested_reply="Thanks, I will review this.",
    )


class ReplyGateTests(unittest.TestCase):
    def test_non_important_reply_is_downgraded_to_review(self):
        result = _enforce_analysis_rules(analysis("Work"), "thread-1")
        self.assertEqual(result.reply_decision, ReplyDecision.review)
        self.assertIsNone(result.suggested_reply)

    def test_important_reply_is_allowed(self):
        result = _enforce_analysis_rules(analysis("Important"), "thread-1")
        self.assertEqual(result.reply_decision, ReplyDecision.reply)
        self.assertTrue(result.suggested_reply)

    def test_latest_user_message_never_gets_a_reply(self):
        result = _enforce_analysis_rules(
            analysis("Important"), "thread-1", latest_sender_is_user=True
        )
        self.assertEqual(result.reply_decision, ReplyDecision.no_reply)
        self.assertIsNone(result.suggested_reply)

    def test_registry_has_three_read_tools_and_one_draft_tool(self):
        descriptions = {item.name: item for item in tool_registry.list_descriptions()}
        self.assertEqual(
            set(descriptions),
            {
                "list_gmail_threads",
                "get_gmail_thread",
                "get_gmail_profile",
                "create_important_reply_draft_tool",
            },
        )
        self.assertEqual(
            descriptions["create_important_reply_draft_tool"].side_effects,
            "creates_draft",
        )


class MailServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_rejects_non_important_category(self):
        row = SimpleNamespace(
            category="Work",
            reply_decision="reply",
            draft_status="none",
            draft_id=None,
            thread_id="thread-1",
        )
        with patch("backend.services.mail_service.get_summary", return_value=row):
            with patch(
                "backend.services.mail_service.integration_service.create_draft",
                new_callable=AsyncMock,
            ) as create_draft:
                with self.assertRaises(PermissionError):
                    await create_important_reply_draft(
                        object(), "user-1", "thread-1", "A reply"
                    )
                create_draft.assert_not_awaited()

    async def test_service_creates_draft_for_important_reply(self):
        row = SimpleNamespace(
            category="Important",
            reply_decision="reply",
            draft_status="none",
            draft_id=None,
            thread_id="thread-1",
        )
        db = SimpleNamespace(commit=Mock())
        with patch("backend.services.mail_service.get_summary", return_value=row):
            with patch(
                "backend.services.mail_service.integration_service.create_draft",
                new_callable=AsyncMock,
                return_value={
                    "draft_id": "draft-1",
                    "thread_id": "thread-1",
                    "status": "draft",
                },
            ):
                result = await create_important_reply_draft(
                    db, "user-1", "thread-1", "A reply"
                )
        self.assertEqual(result["draft_id"], "draft-1")
        self.assertTrue(result["created"])
        self.assertEqual(row.draft_status, "draft")
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
