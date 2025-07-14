import traceback
from typing import Dict, Any
from matrx_utils import settings


async def get_environment(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get environment variables and configuration settings.
    Returns all settings or filtered settings based on a search term.
    
    Args:
        args: Dictionary containing optional parameters:
            - filter: Optional string to filter environment variables by key name
    
    Returns:
        Dictionary with status and result/error information containing environment settings
    """
    try:
        filter_ = args.get('filter')

        if not filter_:
            return {"status": "success", "result": settings.list_settings_redacted()}
        
        filtered_variables = {}
        for k, v in settings.list_settings_redacted().items():
            if str(filter_).lower() in str(k).lower():
                filtered_variables[k] = str(v)

        return {"status": "success", "result": filtered_variables}
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        error_message = f"Error retrieving environment settings: {str(e)}"
        return {"status": "error", "error": error_message, "traceback": error_traceback}


def register_admin_tools(tool_registry):
    """
    Register the admin tools with the tool registry.
    Args:
        tool_registry: The tool registry object
    """
    tool_registry.register_tool(
        name="get_project_environment",
        description="Retrieve environment variables and system configuration settings. Use this to check system configuration, debug environment issues, or verify settings. Sensitive values are automatically redacted for security.",
        parameters={
            "filter": {
                "type": "string",
                "description": "Optional filter to search for specific environment variables by key name. Case-insensitive partial matching is used.",
                "required": False,
            },
        },
        output_schema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["success", "error"],
                    "description": "Operation status",
                },
                "result": {
                    "type": "object",
                    "description": "Dictionary of environment variables and their values (sensitive values are redacted)",
                    "additionalProperties": True,
                },
                "error": {
                    "type": "string",
                    "description": "Error message if operation failed",
                },
                "traceback": {
                    "type": "string",
                    "description": "Error traceback for debugging",
                },
            },
            "required": ["status"],
            "additionalProperties": False,
        },
        annotations=[
            {
                "type": "usage_hint",
                "value": "Use without filter to get all environment variables, or provide a filter string to search for specific settings. Sensitive values like passwords and API keys are automatically redacted for security."
            }
        ],
        function=get_environment,
    )


__all__ = ["get_environment", "register_admin_tools"]