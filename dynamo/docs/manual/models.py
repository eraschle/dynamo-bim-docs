from typing import Generic, List, Optional, TypeVar, cast

from dynamo.docs.docs import IModelDocs
from dynamo.docs.manual.parser import (DocsParser, GroupAnnotationParser,
                                       TParserNode)
from dynamo.docs.manual.sections import DocSection
from dynamo.docs.models.content import ADocContent, IDocContent
from dynamo.models.files import Script
from dynamo.models.model import IAnnotation, IDynamoFile, IGroup, IModelWithId
from dynamo.utils import geom

TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class AFileSectionDocs(ADocContent[TDynamoFile], Generic[TDynamoFile, TParserNode]):

    def __init__(self, file: IModelDocs[TDynamoFile], parser: DocsParser[TParserNode],
                 children: List[IDocContent[TDynamoFile]]) -> None:
        super().__init__(file=file, children=children)
        self._parser = parser

    def _content(self, **kwargs) -> List[str]:
        content = self._get_lines(self._parser.content, self._strip_empty, **kwargs)
        return self.value_handler.as_list(content, default='')

    @property
    def section(self) -> DocSection:
        return self._parser.section


class AnnotationDocs(AFileSectionDocs[TDynamoFile, IAnnotation]):
    def __init__(self, file: IModelDocs[TDynamoFile], parser: DocsParser[IAnnotation],
                 children: List[IDocContent[TDynamoFile]]) -> None:
        super().__init__(file, parser, children)
        self._closest: Optional[IModelWithId] = None

    def linked_node(self, **_) -> IModelWithId:
        if self._closest is not None:
            return self._closest
        distance = None
        for node in self.file.model.nodes:
            if not self.section.is_section_node(self.file.model, node):
                continue
            node_distance = geom.get_distance(node, self._parser.node)
            if distance is None:
                distance = node_distance
            distance = min(node_distance, distance)
            if distance != node_distance:
                continue
            self._closest = node
        if self._closest is None:
            inputs = cast(Script, self.file.model).inputs
            raise AttributeError(
                f'No cloeset Node {self._parser.node} with {self.file.model.nodes} inputs {inputs}'
            )
        return self._closest


class GroupAnnotationDocs(AFileSectionDocs[TDynamoFile, IAnnotation]):

    def __init__(self, file: IModelDocs[TDynamoFile], parser: GroupAnnotationParser) -> None:
        super().__init__(file, parser, children=[])


class GroupsSectionDocs(AFileSectionDocs[TDynamoFile, IGroup]):

    def __init__(self, file: IModelDocs[TDynamoFile], parser: DocsParser[IGroup]) -> None:
        super().__init__(file, parser, self.docs_nodes(file, parser))

    def docs_nodes(self, file: IModelDocs[TDynamoFile],  parser: DocsParser[IGroup]) -> List[IDocContent[TDynamoFile]]:
        nodes = [node for node in parser.node.nodes if isinstance(node, IAnnotation)]
        return [GroupAnnotationDocs(file, GroupAnnotationParser(node)) for node in nodes]
