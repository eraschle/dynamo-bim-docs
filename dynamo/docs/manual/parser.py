from typing import Generic, List, Tuple, TypeVar

from dynamo.models.model import IAnnotation, IGroup

from .sections import GROUP, DocSection, all_doc_sections


def _get_doc_heading(line: str) -> DocSection:
    line = line.strip()
    for section in all_doc_sections():
        if not section.is_section(line):
            continue
        return section
    return DocSection.unknown()


TParserNode = TypeVar('TParserNode', bound=IAnnotation)


class DocsParser(Generic[TParserNode]):

    def __init__(self, node: TParserNode) -> None:
        self.node = node
        self.section, self._lines = self._parse(node)

    def _get_lines(self, node: TParserNode) -> List[str]:
        desc = '' if node.name is None else node.name
        return desc.splitlines(keepends=False)

    def _parse(self, node: TParserNode) -> Tuple[DocSection, List[str]]:
        lines = self._get_lines(node)
        for idx, line in enumerate(lines):
            section = _get_doc_heading(line)
            if DocSection.is_unknown(section):
                continue
            lines = lines[idx:]
            lines[0] = section.clean_value(line)
            return section, lines
        return DocSection.unknown(), []

    def has_section(self) -> bool:
        return not DocSection.is_unknown(self.section)

    def content(self, **kwargs) -> List[str]:
        return self._lines


class AnnotationDocsParser(DocsParser[IAnnotation]):

    def content(self, **kwargs) -> List[str]:
        return self._lines


class GroupAnnotationParser(DocsParser[IAnnotation]):

    def _parse(self, node: IAnnotation) -> Tuple[DocSection, List[str]]:
        return GROUP, self._get_lines(node)


class GroupDocsParser(DocsParser[IGroup]):

    def content(self, **kwargs) -> List[str]:
        return self._lines
