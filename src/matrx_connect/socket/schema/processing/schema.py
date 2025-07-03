from .schema_processor import get_schema_validator as schema_validator


def register_schema(schema):
    schema_validator(schema)


def get_schema_validator():
    return schema_validator(None)