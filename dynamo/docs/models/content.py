from abc import abstractmethod
from pickle import TRUE
from typing import Callable, List, Optional, Protocol, Type, TypeVar

from dynamo.docs.docs import IDocsManager, IExporter, IModelDocs, IValueHandler
from dynamo.models.model import IBaseModel, IFileModel
from dynamo.utils import checks

TFile = TypeVar('TFile', bound=IFileModel)


class IDocContent(Protocol[TFile]):
    file: IModelDocs[TFile]

    @property
    def manager(self) -> IDocsManager:
        ...

    @property
    def exporter(self) -> IExporter:
        ...

    @property
    def model(self) -> TFile:
        ...

    def content(self, level: int, **kwargs) -> List[str]:
        ...

    def has_content(self, **kwargs) -> bool:
        ...


TArg = TypeVar('TArg')


class ADocContent(IDocContent[TFile]):
    def __init__(self, file: IModelDocs[TFile], children: List[IDocContent[TFile]]) -> None:
        self.file = file
        self.children = children

    @property
    def manager(self) -> IDocsManager:
        return self.file.manager

    @property
    def exporter(self) -> IExporter:
        return self.manager.exporter

    @property
    def value_handler(self) -> IValueHandler:
        return self.exporter.value_handler

    def _strip_empty(self, content: List[str]) -> List[str]:
        return self.value_handler.strip_empty(content)

    def _lstrip_empty(self, content: List[str]) -> List[str]:
        return self.value_handler.strip_starting_empty(content)

    def _rstrip_empty(self, content: List[str]) -> List[str]:
        return self.value_handler.strip_ending_empty(content)

    @property
    def model(self) -> TFile:
        return self.file.model

    def _get_args(self, arg_name: str, default: Optional[TArg], **kwargs) -> TArg:
        value = kwargs.get(arg_name, default)
        if value is None or value == default:
            raise ValueError(f'Args "{arg_name}" is None or does not exists')
        return value

    def _get_lines(self, content_cb: Callable[..., List[str]], strip_cb: Optional[Callable[[List[str]], List[str]]] = None, **kwargs) -> List[str]:
        content = content_cb(**kwargs)
        if strip_cb is None:
            strip_cb = self._strip_empty
        content = strip_cb(content)
        return content

    def has_content(self, **kwargs) -> bool:
        return True

    def _is_content(self, content: List[str]) -> bool:
        if len(content) == 1:
            return checks.is_not_blank(content[0])
        return not all(checks.is_blank(line, strip=True) for line in content)

    def content(self, level: int, **kwargs) -> List[str]:
        lines = []
        if self.has_content(**kwargs):
            lines.extend(self.exporter.empty_line())
            lines.extend(self._get_lines(self._content, level=level, **kwargs))

        if self._has_child_content(**kwargs):
            child_content = self._get_lines(
                self._child_content, level=level + 1, **kwargs
            )
            if self._is_content(child_content):
                lines.extend(self.exporter.empty_line())
                lines.extend(child_content)
        return lines

    @abstractmethod
    def _content(self, level: int, **kwargs) -> List[str]:
        pass

    def _has_child_content(self, **kwargs) -> bool:
        if len(self.children) == 0:
            return False
        return any(child.has_content(**kwargs) for child in self.children)

    def _child_content(self, level: int, **kwargs) -> List[str]:
        lines = []
        for child in self.children:
            child_content = self._get_lines(
                child.content, level=level, **kwargs
            )
            if not self._is_content(child_content):
                continue
            lines.extend(self.exporter.empty_line())
            lines.extend(child_content)
        return lines


TNode = TypeVar('TNode', bound=IBaseModel)


class AHeadlineContent(ADocContent[TFile]):

    def __init__(self, file: IModelDocs[TFile], children: List[IDocContent[TFile]]) -> None:
        super().__init__(file, children)
        self._existing_content: List[str] = []

    def _get_node(self, node_type: Type[TNode], **kwargs) -> TNode:
        arg_name = 'node'
        node: TNode = self._get_args(arg_name, None, **kwargs)
        if not isinstance(node, node_type):
            raise ValueError(f'Except "{node_type}" but got {type(node)}')
        return node

    def _get_level(self, **kwargs) -> int:
        arg_name = 'level'
        return self._get_args(arg_name, -1, **kwargs)

    def _content(self, level: int, **kwargs) -> List[str]:
        lines = []
        heading = self._get_lines(self._headline, level=level, **kwargs)
        self._set_existing_content(heading)
        lines.extend(heading)
        content = self._get_lines(
            self._headline_content, level=level, **kwargs
        )
        if self._is_content(content):
            lines.extend(self.exporter.empty_line())
            lines.extend(content)
        return lines

    @abstractmethod
    def _headline(self, level: int, **kwargs) -> List[str]:
        pass

    @abstractmethod
    def _headline_content(self, **kwargs) -> List[str]:
        pass

    def _headline_value(self, lines: List[str]) -> str:
        headline = self.value_handler.strip_starting_empty(lines)
        if len(headline) < 1:
            raise ValueError(f'No Heading in {lines}')
        return headline[0]

    def _set_existing_content(self, heading_lines: List[str]) -> None:
        heading = self._headline_value(heading_lines)
        for line in self.file.existing_docs():
            if len(self._existing_content) == 0 and not line.startswith(heading):
                continue
            elif self._is_next_heading(line):
                break
            self._existing_content.append(line.rstrip())

    def _is_next_heading(self, line: str) -> bool:
        return self.exporter.is_heading(line)

    def _clean_existing_content(self) -> List[str]:
        lines = self._strip_empty(self._existing_content[1:])
        lines = self.value_handler.remove_default_doc(lines)
        return lines

    def _manual_docs(self, default_value: str) -> List[str]:
        existing = self._clean_existing_content()
        existing = self._strip_empty(existing)
        return self.value_handler.as_list(existing, default_value)


class TitleDocContent(ADocContent[TFile]):

    def _content(self, level: int, **kwargs) -> List[str]:
        lines = []
        lines.extend(self.exporter.doc_head())
        lines.extend(self.exporter.empty_line())
        lines.extend(self.exporter.title(self.file))
        return lines


def title_docs(file: IModelDocs[TFile]) -> IDocContent[TFile]:
    return TitleDocContent(file, children=[])
