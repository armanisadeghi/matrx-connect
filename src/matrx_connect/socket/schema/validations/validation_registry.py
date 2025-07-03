from .validation_functions import validate_date_dd_mm_yyyy
from typing import Callable, Dict

# Default validations
VALIDATION_REGISTRY = {
    "validate_date_dd_mm_yyyy": validate_date_dd_mm_yyyy,
}

### Custom validation registry

def register_validation(name: str, validation_function: Callable) -> None:
    global VALIDATION_REGISTRY

    if name in VALIDATION_REGISTRY:
        raise ValueError(f"Validation '{name}' already registered. Please use a different function name.")
    
    VALIDATION_REGISTRY[name] = validation_function


def register_validations(validations: Dict[str, Callable]) -> None:
    for name, validation_function in validations.items():
        register_validation(name, validation_function)