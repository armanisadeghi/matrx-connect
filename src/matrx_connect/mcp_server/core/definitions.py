from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional, List, Awaitable

from jsonschema import validate, ValidationError


@dataclass
class ToolDefinition:
    """
    MCP-compatible tool definition that maintains compatibility with existing systems.
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable[[Dict[str, Any]], Awaitable[Any]]
    output_schema: Dict[str, Any] = None
    annotations: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        # Set default output_schema if not provided
        if self.output_schema is None:
            self.output_schema = {"type": "null"}

        # Validate parameters
        if not isinstance(self.parameters, dict):
            raise ValueError("Parameters must be a dictionary")

        # Validate output_schema
        if not isinstance(self.output_schema, dict):
            raise ValueError("Output schema must be a dictionary")

        # Validate annotations
        if self.annotations is not None:
            if not isinstance(self.annotations, list):
                raise ValueError("Annotations must be a list")
            for ann in self.annotations:
                if not isinstance(ann, dict) or "type" not in ann:
                    raise ValueError("Annotations must be objects with a 'type' field")

        # Validate schemas
        try:
            validate(instance=self.mcp_parameters, schema={"type": "object"})
            validate(instance=self.output_schema, schema={})
        except ValidationError as e:
            raise ValueError(f"Invalid schema: {e}")

    @property
    def mcp_parameters(self) -> Dict[str, Any]:
        """
        Convert the internal parameters format to MCP-compatible JSON Schema format.
        """
        properties = {}
        required = []

        for key, param in self.parameters.items():
            # Extract properties
            prop = {
                "type": param.get("type", "string"),
                "description": param.get("description", ""),
            }

            # Validate array parameters
            if isinstance(prop["type"], str) and prop["type"] == "array" and "items" not in param:
                raise ValueError(f"Parameter '{key}' is an array but missing 'items' schema")

            # Handle array-specific fields
            if "items" in param:
                prop["items"] = self._process_nested_schema(param["items"], for_openai=False)
            if "minItems" in param:
                prop["minItems"] = param["minItems"]
            if "maxItems" in param:
                prop["maxItems"] = param["maxItems"]
            if "uniqueItems" in param:
                prop["uniqueItems"] = param["uniqueItems"]

            # Handle other JSON Schema fields
            if "default" in param:
                prop["default"] = param["default"]
            if "enum" in param:
                prop["enum"] = param["enum"]
            if "minimum" in param:
                prop["minimum"] = param["minimum"]
            if "maximum" in param:
                prop["maximum"] = param["maximum"]
            if "pattern" in param:
                prop["pattern"] = param["pattern"]

            # Handle nested objects
            if prop["type"] == "object" and "properties" in param:
                prop["properties"] = {}
                prop["required"] = param.get("required", [])
                prop["additionalProperties"] = False
                for sub_key, sub_param in param["properties"].items():
                    prop["properties"][sub_key] = self._process_nested_schema(sub_param, for_openai=False)

            properties[key] = prop

            # Track required parameters
            if param.get("required", False):
                required.append(key)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False
        }

    def _process_nested_schema(self, schema: Dict[str, Any], for_openai: bool) -> Dict[str, Any]:
        """
        Process nested schemas, optionally filtering fields unsupported by OpenAI strict mode.

        Args:
            schema: The schema to process.
            for_openai: If True, remove fields not supported in OpenAI strict mode (e.g., minItems).

        Returns:
            Processed schema.
        """
        processed = schema.copy()

        # Fields not supported by OpenAI strict mode
        unsupported_fields = ["minItems", "maxItems", "uniqueItems", "minimum", "maximum", "pattern"]
        if for_openai:
            for field in unsupported_fields:
                processed.pop(field, None)

        if processed.get("type") == "object" and "properties" in processed:
            processed["additionalProperties"] = False
            processed["required"] = processed.get("required", [])
            for sub_key, sub_schema in processed["properties"].items():
                processed["properties"][sub_key] = self._process_nested_schema(sub_schema, for_openai)
        elif processed.get("type") == "array" and "items" in processed:
            processed["items"] = self._process_nested_schema(processed["items"], for_openai)

        return processed

    def to_mcp_format(self) -> Dict[str, Any]:
        """
        Return the tool definition in MCP-compatible format.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.mcp_parameters,
            "output_schema": self.output_schema,
            "annotations": self.annotations or []
        }

    def to_openai_format(self) -> Dict[str, Any]:
        """
        Convert to OpenAI tool format, ensuring compatibility with strict mode.
        """
        # Create a filtered parameters schema for OpenAI strict mode
        properties = {}
        required = []
        for key, param in self.parameters.items():
            prop = {
                "type": param.get("type", "string"),
                "description": param.get("description", ""),
            }
            if "items" in param:
                prop["items"] = self._process_nested_schema(param["items"], for_openai=True)
            if "default" in param:
                prop["default"] = param["default"]
            if "enum" in param:
                prop["enum"] = param["enum"]
            if prop["type"] == "object" and "properties" in param:
                prop["properties"] = {}
                prop["required"] = param.get("required", [])
                prop["additionalProperties"] = False
                for sub_key, sub_param in param["properties"].items():
                    prop["properties"][sub_key] = self._process_nested_schema(sub_param, for_openai=True)
            properties[key] = prop
            if param.get("required", False):
                required.append(key)

        openai_parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False
        }

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": openai_parameters,
            }
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """
        Convert to Anthropic tool format (maintains backward compatibility).
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.mcp_parameters,
        }
