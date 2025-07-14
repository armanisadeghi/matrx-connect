from ..core.registry import tool_registry
from . import math, admin


def register_default_tools():
    math.register_math_tool(tool_registry)
    admin.register_admin_tools(tool_registry)


__all__ = ["register_default_tools"]