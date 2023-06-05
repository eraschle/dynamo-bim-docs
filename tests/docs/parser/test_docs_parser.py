import random
from dataclasses import dataclass
from typing import Optional

from dynamo.docs.manual.models import DESCRIPTION, DocsParser
from dynamo.models.model import IGroup
from dynamo.utils.values import ValueHandler

_TITLE = 'Title'
_CONTENT = ['some content', '', 'other_content']


@dataclass
class AnnotationNode:
    description: str
    node_id: str = ""
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    group: Optional[IGroup] = None


def _section_node(section: str, valid: bool, with_number: bool = False) -> AnnotationNode:
    not_valid_value = '' if valid else ' some text'
    number = f'{random.randrange(1, 100)}' if with_number else ''
    lines = [f'{section}{number} {_TITLE} {section}{not_valid_value}']
    lines.append('')
    lines.extend(_CONTENT)
    lines.append('')
    return AnnotationNode('\n'.join(lines))


def test_parser_has_section():
    node = _section_node(DESCRIPTION.parse_value, valid=True)
    parser = DocsParser(node)
    assert parser.has_section()


def test_parser_has_NOT_section():
    node = _section_node(DESCRIPTION.parse_value, valid=False)
    parser = DocsParser(node)
    assert not parser.has_section()


def test_parser_with_number():
    node = _section_node(DESCRIPTION.parse_value, valid=True, with_number=True)
    parser = DocsParser(node)
    assert isinstance(parser.number(), float)


def test_parser_without_number():
    node = _section_node(DESCRIPTION.parse_value, valid=True, with_number=False)
    parser = DocsParser(node)
    assert parser.number() is None


def test_parser_title():
    node = _section_node(DESCRIPTION.parse_value, valid=True)
    parser = DocsParser(node)
    assert parser.title() == _TITLE


def test_parser_content():
    node = _section_node(DESCRIPTION.parse_value, valid=True)
    parser = DocsParser(node)
    handler = ValueHandler()
    assert len(parser.content(handler)) == len(_CONTENT)
    assert parser.content(handler) == _CONTENT
