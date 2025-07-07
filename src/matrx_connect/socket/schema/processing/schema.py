from .schema_processor import get_schema_validator as schema_validator, get_runtime_schema as runtime_schema
from .default_schema import default_schema

def merge_schemas_with_default(user_schema, base_schema):
    merged = {
        "definitions": base_schema.get("definitions", {}).copy(),
        "tasks": base_schema.get("tasks", {}).copy()
    }

    # Merge user definitions (ignore user's MIC_CHECK_DEFINITION)
    if "definitions" in user_schema:
        for def_name, def_value in user_schema["definitions"].items():
            if def_name != "MIC_CHECK_DEFINITION":
                merged["definitions"][def_name] = def_value

    if "tasks" in user_schema:
        for service_name, service_tasks in user_schema["tasks"].items():
            if service_name not in merged["tasks"]:
                merged["tasks"][service_name] = {}

            for task_name, task_def in service_tasks.items():
                if task_name != "MIC_CHECK":
                    merged["tasks"][service_name][task_name] = task_def

            merged["tasks"][service_name]["MIC_CHECK"] = {
                "$ref": "definitions/MIC_CHECK_DEFINITION"
            }

    for service_name in merged["tasks"]:
        if "MIC_CHECK" not in merged["tasks"][service_name]:
            merged["tasks"][service_name]["MIC_CHECK"] = {
                "$ref": "definitions/MIC_CHECK_DEFINITION"
            }
    return merged


def register_schema(user_schema):
    merged_schema = merge_schemas_with_default(user_schema, default_schema)
    schema_validator(merged_schema)
    return merged_schema


def get_schema_validator():
    return schema_validator(None)


def get_runtime_schema():
    return runtime_schema()