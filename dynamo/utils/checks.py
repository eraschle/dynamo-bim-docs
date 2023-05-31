from typing import Any, Collection, List, Optional, TypeGuard, TypeVar, Union

TValue = TypeVar('TValue', bound=Any | Collection[Any])


def is_none_or_empty(value: Optional[TValue], strip: bool = False) -> TypeGuard[TValue]:
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0
    str_value = value if isinstance(value, str) else str(value)
    str_value = str_value.strip() if strip else str_value
    return len(str_value) == 0


def is_blank(value: Optional[TValue], strip: bool = False) -> TypeGuard[TValue]:
    return is_none_or_empty(value, strip)


def is_not_blank(value: Optional[TValue], strip: bool = False) -> TypeGuard[TValue]:
    return not is_blank(value, strip)
