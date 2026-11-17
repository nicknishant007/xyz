"""Read-only Gmail tools available to the analysis workflow."""
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from backend.services.integration_service import integration_service


class ListThreadsInput(BaseModel):
    query: str = Field(
        default="in:inbox newer_than:30d",
        description="Gmail search query used to select conversations.",
    )
    limit: int = Field(default=200, ge=1, le=500, description="Maximum conversations to return.")


class GetThreadInput(BaseModel):
    thread_id: str = Field(description="ID of the Gmail conversation to retrieve.")


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



@tool
async def get_gmail_profile() -> dict:
    """Return the connected mailbox address and message/thread counts.

    This is a read-only tool and returns fake mailbox metadata in mock mode.
    """
    return await integration_service.get_profile()


READ_ONLY_GMAIL_TOOLS = (list_gmail_threads, get_gmail_thread, get_gmail_profile)
