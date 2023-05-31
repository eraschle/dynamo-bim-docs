from pathlib import Path
from typing import Any, List, Optional, Protocol, Tuple, TypeVar

from dynamo.io.file import IoHandler
from dynamo.models.model import ICustomNode, IFileModel
from dynamo.utils.values import IValueHandler


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


class IExporter(Protocol):
    file_handler: IoHandler
    value_handler: IValueHandler

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
