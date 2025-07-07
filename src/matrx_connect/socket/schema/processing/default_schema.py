default_schema = {
    "definitions": {
        "MIC_CHECK_DEFINITION": {
            "mic_check_message": {
                "REQUIRED": False,
                "DEFAULT": "Service mic check",
                "VALIDATION": None,
                "DATA_TYPE": "string",
                "CONVERSION": None,
                "REFERENCE": None,
                "COMPONENT": "input",
                "COMPONENT_PROPS": {},
                "DESCRIPTION": "Test message for service connectivity",
                "ICON_NAME": "Mic"
            }
        }
    },
    "tasks": {
        "ADMIN_SERVICE": {
            "MIC_CHECK": {
                "$ref": "definitions/MIC_CHECK_DEFINITION"
            },
            "GET_ENVIRONMENT": {
                "redacted": {
                    "REQUIRED": False,
                    "DEFAULT": True,
                    "VALIDATION": None,
                    "DATA_TYPE": "boolean",
                    "CONVERSION": None,
                    "REFERENCE": None,
                    "COMPONENT": "Switch",
                    "COMPONENT_PROPS": {},
                    "ICON_NAME": "EyeOff",
                    "DESCRIPTION": "Hide sensitive values (true) or show all values (false - dangerous!)"
                },
                "filter": {
                    "REQUIRED": False,
                    "DEFAULT": None,
                    "VALIDATION": None,
                    "DATA_TYPE": "string",
                    "CONVERSION": None,
                    "REFERENCE": None,
                    "COMPONENT": "input",
                    "COMPONENT_PROPS": {},
                    "ICON_NAME": "Filter",
                    "TEST_VALUE": "SUPABASE_",
                    "DESCRIPTION": "Only show environment/settings containing this term"
                }
            },
            "LIST_LOGS": {
                "remote_logs": {
                    "REQUIRED": False,
                    "DEFAULT": False,
                    "VALIDATION": None,
                    "DATA_TYPE": "boolean",
                    "CONVERSION": None,
                    "REFERENCE": None,
                    "COMPONENT": "Switch",
                    "COMPONENT_PROPS": {},
                    "ICON_NAME": "Cloud",
                    "DESCRIPTION": "Include remote logs in the listing"
                }
            },
            "GET_LOG": {
                "log_name": {
                    "REQUIRED": True,
                    "DEFAULT": None,
                    "VALIDATION": None,
                    "DATA_TYPE": "string",
                    "CONVERSION": None,
                    "REFERENCE": None,
                    "COMPONENT": "input",
                    "COMPONENT_PROPS": {},
                    "ICON_NAME": "FileText",
                    "DESCRIPTION": "Enter the name of the log file to retrieve"
                },
                "remote_logs": {
                    "REQUIRED": False,
                    "DEFAULT": False,
                    "VALIDATION": None,
                    "DATA_TYPE": "boolean",
                    "CONVERSION": None,
                    "REFERENCE": None,
                    "COMPONENT": "Switch",
                    "COMPONENT_PROPS": {},
                    "ICON_NAME": "Cloud",
                    "DESCRIPTION": "Log type of log name. Remote or Local"
                }
            },
            "TEST_DATABASE_CONNECTION": {
                "database_project_name": {
                    "REQUIRED": True,
                    "DEFAULT": None,
                    "VALIDATION": None,
                    "DATA_TYPE": "string",
                    "CONVERSION": None,
                    "REFERENCE": None,
                    "COMPONENT": "input",
                    "COMPONENT_PROPS": {},
                    "ICON_NAME": "Database",
                    "DESCRIPTION": "Enter the name of the database project to test"
                },
                "table_name": {
                    "REQUIRED": False,
                    "DEFAULT": None,
                    "VALIDATION": None,
                    "DATA_TYPE": "string",
                    "CONVERSION": None,
                    "REFERENCE": None,
                    "COMPONENT": "input",
                    "COMPONENT_PROPS": {},
                    "ICON_NAME": "Table",
                    "DESCRIPTION": "Enter the name of the table to query (optional)"
                },
                "limit": {
                    "REQUIRED": False,
                    "DEFAULT": 10,
                    "VALIDATION": None,
                    "DATA_TYPE": "integer",
                    "CONVERSION": None,
                    "REFERENCE": None,
                    "COMPONENT": "input",
                    "COMPONENT_PROPS": {},
                    "ICON_NAME": "Hash",
                    "TEST_VALUE": 10,
                    "DESCRIPTION": "Maximum number of items to return"
                }
            },
            "GET_REGISTERED_DATABASES": {},
            "GET_REGISTERED_SERVICES": {},
            "GET_APPLICATION_SCHEMA": {}
        }
    }
}