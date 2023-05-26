from typing import Any, Optional, TypeGuard


def is_str(value: Optional[Any]) -> TypeGuard[str]:
    return isinstance(value, str)


def as_str(value: Optional[Any]) -> str:
    return value if is_str(value) else str(value)
