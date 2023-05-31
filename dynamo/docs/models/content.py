from abc import abstractmethod
from ctypes import ArgumentError
from typing import Any, List, Protocol, Type, TypeVar

from dynamo.docs.docs import IDocsManager, IExporter, IModelDocs, IValueHandler
from dynamo.models.model import IBaseModel, IFileModel

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


class ADocContent(IDocContent[TFile]):
    def __init__(self, file: IModelDocs[TFile]) -> None:
        self.file = file

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

    def content(self, level: int, **kwargs) -> List[str]:
        lines = []
        lines.extend(self.exporter.empty_line())
        content = self._content(level, **kwargs)
        lines.extend(self._strip_empty(content))

        lines.extend(self.exporter.empty_line())
        children = self._children_content(level + 1, **kwargs)
        lines.extend(self._strip_empty(children))
        return lines

    @abstractmethod
    def _content(self, level: int, **kwargs) -> List[str]:
        pass

    def _get_content(self, child: IDocContent[Any], level: int, **kwargs) -> List[str]:
        content = child.content(level, **kwargs)
        content = self._rstrip_empty(content)
        return content

    def _children_content(self, level: int, **kwargs) -> List[str]:
        return []


TNode = TypeVar('TNode', bound=IBaseModel)


class AHeadlineContent(ADocContent[TFile]):

    def __init__(self, file: IModelDocs[TFile]) -> None:
        super().__init__(file)
        self._existing_content: List[str] = []

    def _get_node(self, node_type: Type[TNode], **kwargs) -> TNode:
        arg = 'node'
        node = kwargs.get(arg, None)
        if node is None:
            raise ArgumentError(f'Argument "{arg}" is None or does not exists')
        if not isinstance(node, node_type):
            raise ArgumentError(f'Except "{node_type}" but got {type(node)}')
        return node

    def _get_level(self, **kwargs) -> int:
        arg = 'level'
        node = kwargs.get(arg, 0)
        if node < 1:
            raise ArgumentError(f'Argument "{arg}" is None or does not exists')
        return node

    def _content(self, level: int, **kwargs) -> List[str]:
        lines = []
        heading = self._headline(level, **kwargs)
        self._set_existing_content(heading)
        lines.extend(heading)

        lines.extend(self.exporter.empty_line())
        content = self._headline_content(level=level, **kwargs)
        lines.extend(self._strip_empty(content))
        lines = self._rstrip_empty(lines)
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

    def _manual_docs(self) -> List[str]:
        values = self.value_handler
        existing = self._clean_existing_content()
        existing = self._strip_empty(existing)
        return values.as_list(existing, values.default_docs)


class AHeadlineDoc(AHeadlineContent[TFile]):

    def __init__(self, file: IModelDocs[TFile], headline: str) -> None:
        super().__init__(file)
        self.headline = headline

    def _headline(self, level: int, **_) -> List[str]:
        return self.exporter.heading(self.headline, level)


class TitleDocContent(ADocContent[TFile]):

    def _content(self, _: int) -> List[str]:
        lines = []
        lines.extend(self.exporter.doc_head())
        lines.extend(self.exporter.empty_line())
        lines.extend(self.exporter.title(self.file))
        return lines


def title_docs(file: IModelDocs[TFile]) -> IDocContent[TFile]:
    return TitleDocContent(file)
