"""Public agent result schema."""
from pydantic import BaseModel, Field
from backend.schemas.email import EmailAnalysis


class AgentRunResult(BaseModel):
    processed: int = 0
    failed: int = 0
    analyses: list[EmailAnalysis] = Field(default_factory=list)


class EmailAnalysisBatch(BaseModel):
    analyses: list[EmailAnalysis] = Field(min_length=1)
