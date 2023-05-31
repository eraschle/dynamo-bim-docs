from typing import Any, List, Optional, Protocol

from dynamo.models.model import IBaseModel
from dynamo.utils import checks


class IValueHandler(Protocol):
    default_docs: str

    def empty_line(self, amount: int) -> List[str]:
        ...

    def true_value(self, true_value: Optional[str] = None) -> str:
        ...

    def false_value(self, false_value: Optional[str] = None) -> str:
        ...

    def bool_as_str(self, value: bool, true_value: Optional[str] = None, false_value: Optional[str] = None) -> str:
        ...

    def get_or_default(self, value: Any, default: Optional[str] = None) -> List[str]:
        ...

    def list_or_default(self, values: List[Any], default: Optional[str] = None) -> List[str]:
        ...

    def name_or_default(self, model: Optional[IBaseModel], default: Optional[str] = None) -> str:
        ...

    def default_or_empty(self, values: Optional[List[Any]], default: Optional[str] = None) -> List[str]:
        ...

    def strip_starting_empty(self, lines: List[str]) -> List[str]:
        ...

    def strip_ending_empty(self, lines: List[str]) -> List[str]:
        ...

    def strip_empty(self, lines: List[str]) -> List[str]:
        ...

    def remove_default_doc_value(self, lines: List[str]) -> List[str]:
        ...

    def docs_or_manual_docs(self, values: Optional[List[str]]) -> List[str]:
        ...


class ValueHandler(IValueHandler):

    def __init__(self, default_value: str = "Keine Angaben", default_docs: str = "???",
                 true_value: str = "Ja", false_value: str = "Nein") -> None:
        self.default_value = default_value
        self.default_docs = default_docs
        self._true_value = true_value
        self._false_value = false_value

    def empty_line(self, amount: int) -> List[str]:
        return [""] * amount

    def true_value(self, true_value: Optional[str] = None) -> str:
        return true_value or self._true_value

    def false_value(self, false_value: Optional[str] = None) -> str:
        return false_value or self._false_value

    def bool_as_str(self, value: bool, true_value: Optional[str] = None, false_value: Optional[str] = None) -> str:
        return self.true_value(true_value) if value else self.false_value(false_value)

    def _get_default(self, default: Optional[str]) -> str:
        return self.default_value if default is None else default

    def _get_value_or_default(self, value: Any, default: Optional[str] = None) -> str:
        if checks.is_blank(value):
            return self._get_default(default)
        return (value if isinstance(value, str) else str(value)).strip()

    def get_or_default(self, value: Any, default: Optional[str] = None) -> List[str]:
        if isinstance(value, list):
            if len(value) == 0:
                return [self._get_default(default)]
            return [str(val) for val in value]
        return [self._get_value_or_default(value, default)]

    def list_or_default(self, values: List[Any], default: Optional[str] = None) -> List[str]:
        val_or_default = []
        for value in values:
            val_or_default.extend(self.get_or_default(value, default))
        return val_or_default

    def name_or_default(self, model: Optional[IBaseModel], default: Optional[str] = None) -> str:
        if model is None:
            return self._get_default(default)
        return self._get_value_or_default(model.name, default)

    def default_or_empty(self, values: Optional[List[Any]], default: Optional[str] = None) -> List[str]:
        if checks.is_blank(values):
            return [self._get_default(default)]
        return []

    def _can_strip(self, values: List[Any], index: int) -> bool:
        return checks.is_not_blank(values) and checks.is_blank(values[index], strip=True)

    def strip_starting_empty(self, lines: List[str]) -> List[str]:
        while self._can_strip(lines, index=0):
            lines = lines[1:]
        return lines

    def strip_ending_empty(self, lines: List[str]) -> List[str]:
        while self._can_strip(lines, index=-1):
            lines = lines[:-1]
        return lines

    def strip_empty(self, lines: List[str]) -> List[str]:
        lines = self.strip_starting_empty(lines)
        return self.strip_ending_empty(lines)

    def remove_default_doc_value(self, lines: List[str]) -> List[str]:
        while self.default_docs in lines:
            lines.remove(self.default_docs)
        return lines

    def docs_or_manual_docs(self, values: Optional[List[str]]) -> List[str]:
        if not checks.is_blank(values):
            return [self.default_docs]
        return values
