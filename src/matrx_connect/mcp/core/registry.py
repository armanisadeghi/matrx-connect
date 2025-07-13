import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional
import inspect
from matrx_utils import vcprint
from ..core.definitions import ToolDefinition

class ToolRegistry:
    """
    MCP-compatible tool registry that maintains backward compatibility.
    """

    _instance = None

    def __new__(cls, debug: bool = False):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance.tools = {}
            cls._instance.debug = debug
        return cls._instance

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable[[Dict[str, Any]], Awaitable[Any]],
        output_schema: Optional[Dict[str, Any]] = None,
        annotations: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Register a tool with the registry.

        Args:
            name: The unique name of the tool (e.g., 'core_web_search').
            description: A detailed description of the tool's purpose.
            parameters: A dictionary defining input parameters in JSON Schema format.
                       Example:
                       {
                           "param_name": {
                               "type": "string",
                               "description": "Description",
                               "required": True
                           }
                       }
            function: The async function implementing the tool, with signature
                      async def func(args: Dict[str, Any]) -> Dict[str, Any].
            output_schema: Optional JSON Schema defining the tool's output.
                           Defaults to {"type": "null"} if not provided.
            annotations: Optional list of metadata objects with a 'type' field.
                         Defaults to [] if not provided.
                         Example: [{"type": "usage_hint", "value": "Use for web searches"}]
        """
        if name in self.tools:
            raise ValueError("Tool with name {name} is already registered")
        self.tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            function=function,
            output_schema=output_schema,
            annotations=annotations,
        )

        if self.debug:
            vcprint(f"[Matrx Connect MCP TOOL REGISTERED]: {json.dumps(self.tools[name].to_mcp_format(), indent=2)}")

    def get_tools(self, tool_names: List[str], provider: str) -> List[Dict[str, Any]]:
        vcprint(
            data=tool_names,
            title=f"[Matrx Connect MCP TOOL REGISTRY] Getting tools for provider: {provider}",
            color="yellow",
        )
        """
        Get tool definitions in the format required by the specified provider.

        Args:
            tool_names: List of tool names to include
            provider: "anthropic_chat", "openai", or "mcp"

        Returns:
            List of tool definitions in the appropriate format
        """
        tools = []
        for name in tool_names:
            vcprint(f"[Matrx Connect MCP TOOL REGISTRY] Checking tool: {name}", color="yellow")
            if name not in self.tools:
                vcprint(
                    f"[Matrx Connect MCP TOOL REGISTRY] Tool '{name}' not found in registry",
                    color="red",
                )
                continue

            tool_def = self.tools[name]

            if provider == "anthropic_chat":
                tools.append(tool_def.to_anthropic_format())
            elif provider == "mcp":
                tools.append(tool_def.to_mcp_format())
            else:
                tools.append(tool_def.to_openai_format())

        return tools

    def list_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        MCP-compatible method to list all available tools.

        Returns:
            List of tool definitions in MCP format
        """
        return [tool.to_mcp_format() for tool in self.tools.values()]

    def get_tool(self, name):
        if name not in self.tools:
            raise ValueError(f"Tool with name: {name} does not exist")
        return self.tools[name]


tool_registry = ToolRegistry()
