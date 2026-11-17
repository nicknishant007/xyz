"""Tool-calling LangGraph agent with explicit routing and execution limits."""
import asyncio
import json
from typing import Annotated, Any, TypedDict
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from backend.agents.llm import create_gemini_chat_model
from backend.agents.prompts import AGENT_SYSTEM_PROMPT
from backend.agents.tool_registry import tool_registry
from backend.config.settings import settings


MAX_AGENT_TURNS = 4
MAX_TOOL_CALLS = 6
MAX_LLM_RETRIES = 1
MAX_TOOL_RETRIES = 1
MAX_TOOL_RESULT_CHARS = 12000


class ChatAgentState(TypedDict, total=False):
    user_id: str
    messages: Annotated[list[AnyMessage], add_messages]
    agent_turns: int
    tool_calls_used: int
    llm_calls: int
    executed_tools: list[dict[str, str]]


async def call_agent_node(state: ChatAgentState) -> dict[str, Any]:
    """Ask Gemini for a response or tool calls, retrying one transient failure."""
    if settings.mock_ai or not settings.gemini_api_key:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "The request agent needs Gemini. Set GEMINI_API_KEY and "
                        "MOCK_AI=false; mailbox data can remain mocked."
                    )
                )
            ],
            "agent_turns": state.get("agent_turns", 0) + 1,
        }

    model = create_gemini_chat_model().bind_tools(list(tool_registry.get_all()))
    messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT), *state.get("messages", [])]
    llm_calls = state.get("llm_calls", 0)
    for attempt in range(MAX_LLM_RETRIES + 1):
        llm_calls += 1
        try:
            response = await model.ainvoke(messages)
            return {
                "messages": [response],
                "agent_turns": state.get("agent_turns", 0) + 1,
                "llm_calls": llm_calls,
            }
        except Exception:
            if attempt == MAX_LLM_RETRIES:
                return {
                    "messages": [
                        AIMessage(
                            content="Gemini is temporarily unavailable. Please try again shortly."
                        )
                    ],
                    "agent_turns": state.get("agent_turns", 0) + 1,
                    "llm_calls": llm_calls,
                }
            await asyncio.sleep(0.25)
    return {"llm_calls": llm_calls}


def route_after_agent(state: ChatAgentState) -> str:
    """Use tools only when Gemini emitted tool calls and budgets remain."""
    last = state.get("messages", [])[-1]
    if not getattr(last, "tool_calls", None):
        return "finish"
    if state.get("agent_turns", 0) >= MAX_AGENT_TURNS:
        return "limit"
    if state.get("tool_calls_used", 0) >= MAX_TOOL_CALLS:
        return "limit"
    return "execute_tools"


async def execute_tools_node(state: ChatAgentState) -> dict[str, Any]:
    """Execute only allowlisted tools; inject trusted identity and bound retries/output."""
    last = state.get("messages", [])[-1]
    calls = getattr(last, "tool_calls", []) or []
    used = state.get("tool_calls_used", 0)
    results: list[ToolMessage] = []
    activity = list(state.get("executed_tools", []))

    for call in calls:
        name = str(call.get("name", ""))
        call_id = str(call.get("id") or f"tool-call-{used + 1}")
        args = dict(call.get("args") or {})
        if used >= MAX_TOOL_CALLS:
            content = "Tool call budget exceeded. Stop requesting tools."
            activity.append({"name": name or "unknown", "status": "limit"})
            results.append(ToolMessage(content=content, tool_call_id=call_id))
            continue

        used += 1
        if name == "create_important_reply_draft_tool":
            # Do not trust a model-supplied identity; always use the authenticated session.
            args["user_id"] = state["user_id"]

        safe_error = "Tool failed. Check the request and try a narrower query."
        for attempt in range(MAX_TOOL_RETRIES + 1):
            try:
                result = await tool_registry.ainvoke(name, args)
                content = json.dumps(result, ensure_ascii=False, default=str)
                if len(content) > MAX_TOOL_RESULT_CHARS:
                    content = content[:MAX_TOOL_RESULT_CHARS] + "\n[Tool output truncated.]"
                activity.append({"name": name, "status": "ok"})
                break
            except (LookupError, PermissionError, ValueError) as exc:
                content = str(exc)
                activity.append({"name": name or "unknown", "status": "rejected"})
                break
            except Exception:
                if attempt == MAX_TOOL_RETRIES:
                    content = safe_error
                    activity.append({"name": name or "unknown", "status": "failed"})
                else:
                    await asyncio.sleep(0.25)
        results.append(ToolMessage(content=content, tool_call_id=call_id))

    return {
        "messages": results,
        "tool_calls_used": used,
        "executed_tools": activity,
    }


def route_after_tools(state: ChatAgentState) -> str:
    if state.get("tool_calls_used", 0) >= MAX_TOOL_CALLS:
        return "limit"
    if state.get("agent_turns", 0) >= MAX_AGENT_TURNS:
        return "limit"
    return "agent"


def request_limit_node(state: ChatAgentState) -> dict[str, Any]:
    return {
        "messages": [
            AIMessage(
                content=(
                    "I reached the request's tool or reasoning limit. I stopped safely; "
                    "please ask a narrower question."
                )
            )
        ]
    }


def build_chat_agent_graph():
    graph = StateGraph(ChatAgentState)
    graph.add_node("agent", call_agent_node)
    graph.add_node("execute_tools", execute_tools_node)
    graph.add_node("request_limit", request_limit_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "execute_tools": "execute_tools",
            "finish": END,
            "limit": "request_limit",
        },
    )
    graph.add_conditional_edges(
        "execute_tools",
        route_after_tools,
        {
            "agent": "agent",
            "limit": "request_limit",
        },
    )
    graph.add_edge("request_limit", END)
    return graph.compile()


chat_agent_graph = build_chat_agent_graph()


async def run_chat_agent(user_id: str, message: str) -> dict[str, Any]:
    """Run one stateless user request with hard limits on tools and model calls."""
    result = await chat_agent_graph.ainvoke(
        {
            "user_id": user_id,
            "messages": [HumanMessage(content=message)],
            "agent_turns": 0,
            "tool_calls_used": 0,
            "llm_calls": 0,
            "executed_tools": [],
        }
    )
    last = result["messages"][-1]
    reply = last.content if isinstance(last.content, str) else json.dumps(last.content, default=str)
    return {
        "reply": reply,
        "tool_calls_used": result.get("tool_calls_used", 0),
        "llm_calls": result.get("llm_calls", 0),
        "executed_tools": result.get("executed_tools", []),
    }
