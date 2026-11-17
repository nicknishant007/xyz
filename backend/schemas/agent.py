"""Request and response models for the conversational mailbox agent."""
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AgentChatResponse(BaseModel):
    reply: str
    tool_calls_used: int
    llm_calls: int
    executed_tools: list[dict[str, str]]
