from pathlib import Path
from typing import Any, List, Optional, Protocol, Tuple, TypeVar

from dynamo.io.file import FileHandler
from dynamo.models.model import IBaseModel, ICustomNode, IFileModel
from dynamo.utils import checks


class IDocsFile(Protocol):
    manager: 'IDocsManager'

    @property
    def src_path(self) -> Path:
        ...

    @property
    def doc_path(self) -> Path:
        ...

    @property
    def display_name(self) -> str:
        ...

    def existing_docs(self) -> List[str]:
        ...


TModel = TypeVar('TModel', bound=IFileModel)


class IModelDocs(IDocsFile, Protocol[TModel]):
    model: TModel

    def write(self, lines: List[str]):
        ...


class ValueHandler:

    def __init__(self, default_value: str = "Keine Angaben", no_manual_doc: str = "???",
                 true_value: str = "Ja", false_value: str = "Nein") -> None:
        self.default_value = default_value
        self.no_manual_doc = no_manual_doc
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
        return value if isinstance(value, str) else str(value).strip()

    def value_or_default(self, value: Any, default: Optional[str] = None) -> List[str]:
        if isinstance(value, list):
            if len(value) == 0:
                return [self._get_default(default)]
            return [str(val) for val in value]
        return [self._get_value_or_default(value, default)]

    def values_or_default(self, values: List[Any], default: Optional[str] = None) -> List[str]:
        val_or_default = []
        for value in values:
            val_or_default.extend(self.value_or_default(value, default))
        return val_or_default

    def name_or_default(self, model: Optional[IBaseModel], default: Optional[str] = None) -> str:
        if model is None:
            return self._get_default(default)
        return self._get_value_or_default(model.name, default)

    def default_if_empty(self, values: Optional[List[Any]], default: Optional[str] = None) -> List[str]:
        if values is None or checks.is_blank(values):
            return [self._get_default(default)]
        return []

    def __is_blank(self, value: Any, strip: bool = True) -> bool:
        return checks.is_blank(value, strip=strip)

    def remove_starting_empty_lines(self, lines: List[str]) -> List[str]:
        return checks.remove_starting_of(lines, self.__is_blank)

    def remove_ending_empty_lines(self, lines: List[str]) -> List[str]:
        return checks.remove_ending_of(lines, self.__is_blank)

    def remove_starting_and_ending_empty_lines(self, lines: List[str]) -> List[str]:
        lines = self.remove_starting_empty_lines(lines)
        return self.remove_ending_empty_lines(lines)

    def remove_no_manual_docs(self, lines: List[str]) -> List[str]:
        while self.no_manual_doc in lines:
            lines.remove(self.no_manual_doc)
        return lines

    def manual_docs(self, values: Optional[List[str]]) -> List[str]:
        if values is None or len(values) == 0:
            return [self.no_manual_doc]
        return values


class IExporter(Protocol):
    handler: FileHandler
    values: ValueHandler

    def empty_line(self, amount: int = 1) -> List[str]:
        ...

    def doc_head(self) -> List[str]:
        ...

    def title(self, file: IDocsFile) -> List[str]:
        ...

    def heading(self, name: str, level: int) -> List[str]:
        ...

    def is_heading(self, value: str) -> bool:
        ...

    def as_list(self, values: List[str]) -> List[str]:
        ...

    def url_link(self, url: str, display_name: Optional[str]) -> List[str]:
        ...

    def file_link(self, file: IDocsFile, relative_to: IDocsFile) -> str:
        ...

    def link_indexes(self, lines: List[str]) -> List[Tuple[int, str, Optional[str]]]:
        ...

    def as_file_link_list(self, values: List[Tuple[IDocsFile, IDocsFile]]) -> List[str]:
        ...

    def as_table(self, heading: Optional[List[str]], lines: List[List[Any]]) -> List[str]:
        ...

    def table_ranges(self, lines: List[str]) -> List[Tuple[int, int]]:
        ...

    def as_code(self, code: str, language: str, indent: int) -> List[str]:
        ...


class IDocsManager(Protocol):
    exporter: IExporter

    @property
    def doc_root(self) -> Path:
        ...

    @property
    def script_src_path(self) -> Path:
        ...

    @property
    def script_doc_path(self) -> Path:
        ...

    @property
    def package_src_path(self) -> Path:
        ...

    @property
    def package_doc_path(self) -> Path:
        ...

    def switch_path(self, path: Path) -> Path:
        ...

    def doc_file_of(self, node: ICustomNode) -> Optional[IDocsFile]:
        ...
