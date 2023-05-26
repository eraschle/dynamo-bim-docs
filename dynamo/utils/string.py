from typing import Any, Dict, Iterable, Optional

from dynamo.utils.checks import is_blank


DEFAULT_VALUE = "Keine Angaben"


def value_or_default(value: Optional[Any]) -> Any:
    if is_blank(value):
        return DEFAULT_VALUE
    return value


CLEAN_SPACE_VALUES = [
    '_'
]


def replace_with_space(value: str, replace_values: Iterable[str] = CLEAN_SPACE_VALUES) -> str:
    for srch in replace_values:
        value = value.replace(srch, ' ')
    return value.strip()


CLEAN_VALUES = {
    '%': '',
    '[': '',
    ']': '',
    '%': '',
    '&': '',
    'ꟿ': '',
    '(': '',
    ')': '',
    '.': '-'
}


def clean_value(value: str, replace_values: Dict[str, str] = CLEAN_VALUES) -> str:
    for srch, repl in replace_values.items():
        value = value.replace(srch, repl)
    return value.strip()
