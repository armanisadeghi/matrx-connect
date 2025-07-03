from typing import Any, Type
from enum import Enum
from datetime import datetime

def validate_enum(value: Any, enum_type: Type[Enum]) -> None:
    """
    Ensures the value is a valid member of an Enum.
    """
    if value not in enum_type.__members__.values():
        raise ValueError(f"Invalid value '{value}'. Must be one of {list(enum_type.__members__.values())}")

def validate_date_dd_mm_yyyy(value: Any) -> None:
    try:
        datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        raise ValueError(f"Invalid date format '{value}'. Must be in the format DD/MM/YYYY.")

