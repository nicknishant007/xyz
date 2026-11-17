"""Explicit allowlist and metadata registry for agent-callable tools."""
from dataclasses import dataclass
from typing import Any
from langchain_core.tools import BaseTool
from backend.tools.gmail_tools import GMAIL_TOOLS


@dataclass(frozen=True)
class ToolDescription:
    name: str
    description: str
    input_schema: dict[str, Any]
    side_effects: str


class ToolRegistry:
    """Only registered tools can be invoked by an agent."""

    def __init__(self, tools: tuple[BaseTool, ...]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ValueError(f"Tool is not allowed: {name}") from exc

    def list_descriptions(self) -> list[ToolDescription]:
        return [
            ToolDescription(
                name=tool.name,
                description=tool.description,
                input_schema=tool.args_schema.model_json_schema(),
                side_effects=(tool.metadata or {}).get("side_effects", "read_only"),
            )
            for tool in self._tools.values()
        ]

    async def ainvoke(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self.get(name)
        return await tool.ainvoke(arguments)


tool_registry = ToolRegistry(GMAIL_TOOLS)
