from ..core.registry import tool_registry
from . import math


def register_default_tools():
    math.register_math_tool(tool_registry)


__all__ = ["register_default_tools"]