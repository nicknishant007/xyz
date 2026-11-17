"""LangChain model invocation for Google Gemini structured email analysis."""
import json
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config.settings import settings


def create_gemini_chat_model() -> ChatGoogleGenerativeAI:
    """Create the configured LangChain Gemini chat model for tool calling."""
    if not settings.gemini_api_key:
        raise RuntimeError("Set GEMINI_API_KEY to use Google Gemini.")
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=0,
    )


async def invoke_gemini(schema: type, system_prompt: str, payload: dict[str, Any]) -> Any:
    """Call the configured Gemini model through LangChain and parse structured output."""
    chat_model = create_gemini_chat_model()
    structured_model = chat_model.with_structured_output(schema, method="json_schema")
    return await structured_model.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
    )
