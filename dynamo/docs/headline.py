from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Generic, Iterable, List, Optional, TypeVar

from dynamo.docs.content import AHeadlineDoc, IDocContent, TFile
from dynamo.docs.docs import IExporter, IModelDocs
from dynamo.models.model import IAnnotation, IDynamoFile, IGroup, IModelWithId, INode
from dynamo.utils import geom


class DocType(Enum):
    HEADING = auto()
    NODE = auto()


@dataclass(slots=True, frozen=True, kw_only=True)
class DocSection:
    @classmethod
    def unknown(cls) -> 'DocSection':
        return DocSection(title='UNKNOWN', parse_value='', doc_type=DocType.HEADING)

    @classmethod
    def is_unknown(cls, docs: 'DocSection') -> bool:
        return docs == cls.unknown()

    title: str = field(hash=True)
    parse_value: str = field(compare=False)
    doc_type: DocType = field(compare=False)

    def is_section(self, value: str) -> bool:
        return value.startswith(self.parse_value) and value.endswith(self.parse_value)

    def is_type(self, doc_type: DocType) -> bool:
        return self.doc_type == doc_type


INFO = DocSection(title='Informationen', doc_type=DocType.HEADING, parse_value='')
DOCS = DocSection(title='Anleitung', doc_type=DocType.HEADING, parse_value='')
INPUT = DocSection(title='Eingabe', doc_type=DocType.HEADING, parse_value='<<')
OUTPUT = DocSection(title='Ausgabe', doc_type=DocType.HEADING, parse_value='>>')
FILES = DocSection(title='Dateien', doc_type=DocType.HEADING, parse_value='')
SOLUTION = DocSection(title='Problem / Lösung', doc_type=DocType.HEADING, parse_value='??')
KNOWN_WARNING = DocSection(title='Warnungen', doc_type=DocType.NODE, parse_value='!!')


def _doc_sections() -> Iterable[DocSection]:
    return [inst for _, inst in globals().items() if isinstance(inst, DocSection)]


def _get_doc_heading(line: str) -> DocSection:
    line = line.strip()
    for section in _doc_sections():
        if not section.is_section(line):
            continue
        return section
    return DocSection.unknown()


class DocsParser:
    def __init__(self, node: IAnnotation) -> None:
        self.node = node
        self._lines = self.node.description.splitlines(keepends=False)
        self._section = DocSection.unknown()
        self._start_idx: int = -1

    def _parse(self) -> None:
        for idx, line in enumerate(self._lines):
            section = _get_doc_heading(line)
            if DocSection.is_unknown(section):
                continue
            self._section = section
            self._start_idx = idx

    def is_doc_type(self, doc_type: DocType) -> bool:
        return self._section.doc_type == doc_type

    def has_section(self) -> bool:
        return not DocSection.is_unknown(self._section)

    def number(self) -> str:
        line = self._lines[self._start_idx]
        return line.replace(self._section.parse_value, '').strip()

    def title(self) -> str:
        line = self._lines[self._start_idx]
        return line.replace(self._section.parse_value, '').strip()

    def content(self, exporter: IExporter, **kwargs) -> List[str]:
        doc_lines = self._lines[self._start_idx+1:]
        return exporter.value_handler.strip_empty(doc_lines)


class SectionDocs(AHeadlineDoc[TFile]):
    def __init__(self, file: IModelDocs[TFile], parser: DocsParser) -> None:
        super().__init__(file, parser.title())
        self._parser = parser

    @property
    def section(self) -> DocSection:
        return self._parser._section

    def _heading_content(self, **kwargs) -> List[str]:
        return self._parser.content(self.exporter, **kwargs)


class AnnotationDocs(SectionDocs[TFile]):

    def __init__(self, file: IModelDocs[TFile], parser: DocsParser) -> None:
        super().__init__(file, parser)
        self._closest: Optional[IModelWithId] = None

    def linked_node(self, **_) -> IModelWithId:
        if self._closest is not None:
            return self._closest
        if self._parser.is_doc_type(DocType.HEADING):
            raise ValueError(f'{DocType.HEADING} is not allowed')
        distance = None
        for node in self.file.model.nodes:
            node_distance = geom.get_distance(node, self._parser.node)
            if distance is None:
                distance = node_distance
            distance = min(node_distance, distance)
            if distance != node_distance:
                continue
            self._closest = node
        if self._closest is None:
            raise AttributeError(f'No cloeset Node found for {self.content}')
        return self._closest


class GroupsDocs(SectionDocs[TFile]):

    def linked_nodes(self, **_) -> List[IModelWithId]:
        if not isinstance(self._parser.node, IGroup):
            raise RuntimeError(f'Expect "IGroup" but got {type(self._parser.node)}')
        return self._parser.node.nodes


TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class DocsNodeFactory:

    def _docs_parser(self, node: IAnnotation) -> Optional[DocsParser]:
        parser = DocsParser(node)
        if not parser.has_section():
            return None
        return parser

    def group_docs(self, file: IModelDocs[TDynamoFile]) -> List[GroupsDocs]:
        doc_models = []
        for group_node in file.model.groups:
            parser = self._docs_parser(group_node)
            if parser is None:
                continue
            doc_model = GroupsDocs(file, parser)
            doc_models.append(doc_model)
        return doc_models

    def annotation_docs(self, file: IModelDocs[TDynamoFile]) -> List[AnnotationDocs]:
        doc_models = []
        for group_node in file.model.annotations:
            parser = self._docs_parser(group_node)
            if parser is None:
                continue
            doc_model = AnnotationDocs(file, parser)
            doc_models.append(doc_model)
        return doc_models


class DocsNodeRepository(Generic[TDynamoFile]):
    def __init__(self, file: IModelDocs[TDynamoFile], factory: DocsNodeFactory) -> None:
        self.file = file
        self._group_sections: Dict[DocSection, List[SectionDocs[IDynamoFile]]] = {}
        self._add_group_docs(factory)
        self._annotation_docs: List[AnnotationDocs[IDynamoFile]] = []
        self._add_annotation_docs(factory)

    def _add_group_docs(self, factory: DocsNodeFactory) -> None:
        for content in factory.group_docs(self.file):
            section = content.section
            if section not in self._group_sections:
                self._group_sections[section] = []
            self._group_sections[section].append(content)

    def _add_annotation_docs(self, factory: DocsNodeFactory) -> None:
        for content in factory.annotation_docs(self.file):
            self._annotation_docs.append(content)

    def section_doc(self, section: DocSection) -> List[SectionDocs[IDynamoFile]]:
        return self._group_sections.get(section, [])

    def node_docs(self, model: IModelWithId) -> Optional[IDocContent[IDynamoFile]]:
        for docu in self._annotation_docs:
            node_doc = docu.linked_node()
            if model.node_id != node_doc.node_id:
                continue
            return docu
        return None
