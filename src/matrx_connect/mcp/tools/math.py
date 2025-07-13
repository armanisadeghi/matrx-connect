from typing import Dict, Any
import math


async def calculate(args: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a mathematical expression."""
    expression = args["expression"]
    try:
        # Basic safety check to prevent dangerous operations
        if any(op in expression for op in ["import", "exec", "eval", "os", "sys"]):
            return {
                "status": "error",
                "error": "Invalid expression: contains forbidden operations",
            }

        # Create a safe math environment
        safe_math = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "sqrt": math.sqrt,
            "pi": math.pi,
            "e": math.e,
        }

        result = eval(expression, {"__builtins__": {}}, safe_math)
        return {"status": "success", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def register_math_tool(registry):
    """Register the math calculation tool with the provided registry."""
    registry.register_tool(
        name="core_math_calculate",
        description="Evaluates a mathematical expression with basic arithmetic and trigonometric functions.",
        parameters={
            "expression": {
                "type": "string",
                "description": "Mathematical expression (e.g., '2 + 2' or 'sin(3.14)').",
                "required": True,
                "pattern": "^\\s*(?:[0-9]+\\.?[0-9]*([eE][+-]?[0-9]+)?|sin|cos|tan|sqrt|pi|e|\\(|\\)|\\+|\\-|\\*|\\/|\\s)+\\s*$"
            }
        },
        output_schema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["success", "error"],
                    "description": "Operation status."
                },
                "result": {
                    "type": "number",
                    "description": "Result of the mathematical expression, if successful.",
                    "nullable": True
                },
                "error": {
                    "type": "string",
                    "description": "Error message if the operation fails.",
                    "nullable": True
                }
            },
            "required": ["status"],
            "additionalProperties": False
        },
        annotations=[{"type": "usage_hint", "value": "Use to evaluate mathematical expressions"}],
        function=calculate
    )


__all__ = ["calculate", "register_math_tool"]
