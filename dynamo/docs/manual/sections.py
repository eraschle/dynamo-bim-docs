from abc import abstractmethod
from typing import Iterable

from dynamo.models.files import Script
from dynamo.models.model import IDynamoFile, IModelWithId, INode


class DocSection:
    @classmethod
    def unknown(cls) -> 'DocSection':
        return DocSection(title='UNKNOWN', parse_value='')

    @classmethod
    def is_unknown(cls, docs: 'DocSection') -> bool:
        return docs == cls.unknown()

    def __init__(self, parse_value: str, title: str) -> None:
        self.title = title
        self._parse_value = parse_value

    @property
    @abstractmethod
    def parse_value(self) -> str:
        pass

    def is_section(self, value: str) -> bool:
        if len(self.parse_value) == 0:
            return False
        return value.startswith(self.parse_value)

    def clean_value(self, value: str) -> str:
        return value.replace(self.parse_value, '').strip()

    def is_section_node(self, file: IDynamoFile, node: IModelWithId) -> bool:
        return node in file.nodes

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DocSection):
            return False
        return self.title == other.title


class HeadlineDocSection(DocSection):

    @property
    def parse_value(self) -> str:
        return self._parse_value

    def clean_value(self, value: str) -> str:
        return value


class NodeDocSection(DocSection):

    @property
    def parse_value(self) -> str:
        return f'-{self._parse_value}-'


class GroupAnnptationSection(NodeDocSection):

    @property
    def parse_value(self) -> str:
        return self._parse_value


class InputDocSection(NodeDocSection):

    def is_section_node(self, file: IDynamoFile, node: IModelWithId) -> bool:
        if not isinstance(file, Script) or not isinstance(node, INode):
            return False
        return node.is_input or node in file.inputs


class OutputDocSection(NodeDocSection):

    def is_section_node(self, file: IDynamoFile, node: IModelWithId) -> bool:
        if not isinstance(file, Script) or not isinstance(node, INode):
            return False
        return node.is_output or node in file.outputs


DESCRIPTION = HeadlineDocSection(title='Beschreibung', parse_value='Beschreibung')
DOCS = HeadlineDocSection(title='Anleitung', parse_value='Anleitung')
GROUP = GroupAnnptationSection(title='GROUP', parse_value='')
WARNINGS = NodeDocSection(title='Warnungen', parse_value='WARN')
INPUT = InputDocSection(title='Eingang', parse_value='IN')
OUTPUT = OutputDocSection(title='Ausgang', parse_value='OUT')


def all_doc_sections() -> Iterable[DocSection]:
    sections = [inst for _, inst in globals().items() if isinstance(inst, DocSection)]
    sections = [section for section in sections if section is not GROUP]
    return sections
