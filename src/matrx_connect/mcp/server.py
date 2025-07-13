from typing import Any, Dict, List
import inspect

from jsonschema import validate
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool as MCPTool

from . import tool_registry


class BridgedMCP(FastMCP):
    async def list_tools(self) -> List[MCPTool]:
        return [
            MCPTool(
                name=tool_def["name"],
                description=tool_def["description"],
                inputSchema=tool_def["input_schema"],
                outputSchema=tool_def["output_schema"],
                annotations={ann["type"]: ann["value"] for ann in tool_def["annotations"]}
            ) for tool_def in tool_registry.list_mcp_tools()
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_def = tool_registry.get_tool(name)
        try:
            if inspect.iscoroutinefunction(tool_def.function):
                result = await tool_def.function(arguments)
            else:
                result = tool_def.function(arguments)

            validate(instance=result, schema=tool_def.output_schema)

            return result
        except Exception as e:
            raise ValueError(f"Error in {name}: {str(e)}")


mcp = BridgedMCP(name="MCP Server")
