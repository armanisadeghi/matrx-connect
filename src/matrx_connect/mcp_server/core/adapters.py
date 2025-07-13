from typing import List, Dict, Any
from .registry import tool_registry


def get_openai_compatible_tools(tool_names: List[str]) -> List[Dict[str, Any]]:
    return tool_registry.get_tools(tool_names, provider="openai")


def get_anthropic_compatible_tools(tool_names: List[str]) -> List[Dict[str, Any]]:
    return tool_registry.get_tools(tool_names, provider="anthropic_chat")


def get_mcp_compatible_tools(tool_names: List[str]) -> List[Dict[str, Any]]:
    return tool_registry.get_tools(tool_names, provider="mcp")


__all__ = [
    "get_openai_compatible_tools",
    "get_anthropic_compatible_tools",
    "get_mcp_compatible_tools",
]
