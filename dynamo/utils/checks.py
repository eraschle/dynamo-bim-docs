from typing import Any, Callable, Collection, List, Optional, Union


def is_none_or_empty(value: Any, strip: bool = False) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0
    if not isinstance(value, str):
        value = str(value)
    if strip:
        value = value.strip()
    return len(value) == 0


def is_blank(value: Optional[Union[str, Collection[Any]]], strip: bool = False) -> bool:
    return is_none_or_empty(value, strip)


def is_not_blank(value: Union[str, Collection], strip: bool = False) -> bool:
    return not is_blank(value, strip)


def remove_starting_of(lines: List[Any], callback: Callable[[Any], bool]) -> List[Any]:
    while is_not_blank(lines) and callback(lines[0]):
        lines = lines[1:]
    return lines


def remove_ending_of(lines: List[Any], callback: Callable[[Any], bool]) -> List[Any]:
    while is_not_blank(lines) and callback(lines[-1]):
        lines = lines[:-1]
    return lines
