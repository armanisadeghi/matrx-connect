from typing import Callable, Dict


CUSTOM_CONVERSIONS = {
}


def register_conversion(name: str, conversion_function: Callable) -> None:
    global CUSTOM_CONVERSIONS 
    if name in CUSTOM_CONVERSIONS:
        raise ValueError(f"Conversion '{name}' already registered. Please use a different function name.")
    CUSTOM_CONVERSIONS[name] = conversion_function

def register_conversions(conversions: Dict[str, Callable]) -> None:
    for name, conversion_function in conversions.items():
        register_conversion(name, conversion_function)