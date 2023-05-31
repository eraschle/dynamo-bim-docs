from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Iterable, List, Optional

from dynamo.docs.docs import IModelDocs, IValueHandler
from dynamo.docs.models.content import AHeadlineDoc, TFile
from dynamo.models.model import IAnnotation, IGroup, IModelWithId
from dynamo.utils import geom


class DocType(Enum):
    HEADING = auto()
    NODE = auto()


@dataclass(slots=True, frozen=True, kw_only=True, eq=True)
class DocSection:
    @classmethod
    def unknown(cls) -> 'DocSection':
        return DocSection(title='UNKNOWN', parse_value='', doc_type=DocType.HEADING)

    @classmethod
    def is_unknown(cls, docs: 'DocSection') -> bool:
        return docs == cls.unknown()

    title: str
    parse_value: str = field(compare=False, repr=False)
    doc_type: DocType = field(compare=False, repr=True)

    def is_section(self, value: str) -> bool:
        if len(self.parse_value) == 0:
            return False
        return value.startswith(self.parse_value) and value.endswith(self.parse_value)

    def is_type(self, doc_type: DocType) -> bool:
        return self.doc_type == doc_type


def get_parse_value(value: str) -> str:
    return f'>{value}<'


def _section(title: str, parse_value: str, doc_type: DocType = DocType.HEADING) -> DocSection:
    parse_value = get_parse_value(parse_value)
    return DocSection(title=title, doc_type=doc_type, parse_value=parse_value)


INFO = _section(title='Informationen', parse_value='I')
DESCRIPTION = _section(title='Beschreibung', parse_value='B')
DOCS = _section(title='Anleitung', parse_value='D')
INPUT = _section(title='Eingabe', parse_value='E')
OUTPUT = _section(title='Ausgabe', parse_value='A')
FILES = _section(title='Dateien', parse_value='F')
SOLUTION = _section(title='Problem / Lösung', parse_value='?')
KNOWN_WARNING = _section(title='Warnungen', parse_value='!')


def _doc_sections() -> Iterable[DocSection]:
    sections = [inst for _, inst in globals().items() if isinstance(inst, DocSection)]
    return sections


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
        self._lines = self._get_lines()
        self._section = DocSection.unknown()
        self._start_idx: int = -1
        self._parse()

    def _get_lines(self) -> List[str]:
        desc = "" if self.node.description is None else self.node.description
        return desc.splitlines(keepends=False)

    def _parse(self) -> None:
        for idx, line in enumerate(self._lines):
            section = _get_doc_heading(line)
            if DocSection.is_unknown(section):
                continue
            self._section = section
            self._start_idx = idx
            break

    def is_doc_type(self, doc_type: DocType) -> bool:
        return self._section.doc_type == doc_type

    def has_section(self) -> bool:
        return not DocSection.is_unknown(self._section)

    def _splitted_first_line(self) -> List[str]:
        line = self._lines[self._start_idx]
        line = line.replace(self._section.parse_value, '').strip()
        return line.split(' ')

    def _has_number(self, values: List[str]) -> Optional[float]:
        return values[0].strip().isnumeric()

    def number(self) -> Optional[float]:
        values = self._splitted_first_line()
        if not self._has_number(values):
            return None
        return float(values[0].strip())

    def title(self) -> str:
        values = self._splitted_first_line()
        if self._has_number(values):
            values = values[1:]
        return ' '.join([val.strip() for val in values])

    def content(self, value_handler: IValueHandler) -> List[str]:
        doc_lines = self._lines[self._start_idx+1:]
        return value_handler.strip_empty(doc_lines)


class SectionDocs(AHeadlineDoc[TFile]):
    def __init__(self, file: IModelDocs[TFile], parser: DocsParser) -> None:
        super().__init__(file, parser.title())
        self._parser = parser

    @property
    def section(self) -> DocSection:
        return self._parser._section

    def _headline_content(self, **kwargs) -> List[str]:
        return self._parser.content(self.exporter.value_handler, **kwargs)


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
