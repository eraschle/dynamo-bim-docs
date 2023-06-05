from typing import Generic, List, Optional, TypeVar

from dynamo.docs.docs import IModelDocs
from dynamo.docs.manual.parser import TParserNode
from dynamo.docs.manual.sections import WARNINGS
from dynamo.docs.models.content import IDocContent
from dynamo.models.model import IDynamoFile, IModelWithId

from .models import AnnotationDocs, DocSection, DocsParser, GroupsSectionDocs

TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class DocsNodeFactory:

    def _docs_parser(self, node: TParserNode) -> Optional[DocsParser[TParserNode]]:
        parser = DocsParser(node)
        if not parser.has_section():
            return None
        return parser

    def group_docs(self, file: IModelDocs[TDynamoFile]) -> List[GroupsSectionDocs]:
        doc_models = []
        for node in file.model.groups:
            parser = self._docs_parser(node)
            if parser is None:
                continue
            doc_model = GroupsSectionDocs(file, parser)
            doc_models.append(doc_model)
        return doc_models

    def annotation_docs(self, file: IModelDocs[TDynamoFile]) -> List[AnnotationDocs]:
        doc_models = []
        for node in file.model.annotations:
            parser = self._docs_parser(node)
            if parser is None:
                continue
            doc_model = AnnotationDocs(file, parser, children=[])
            doc_models.append(doc_model)
        return doc_models


class DocsNodeRepository(Generic[TDynamoFile]):
    def __init__(self, file: IModelDocs[TDynamoFile], factory: DocsNodeFactory) -> None:
        self.file = file
        self._groups: List[GroupsSectionDocs[IDynamoFile]] = []
        self._add_group_docs(factory)
        self._annotations: List[AnnotationDocs[IDynamoFile]] = []
        self._add_annotation_docs(factory)

    def _add_group_docs(self, factory: DocsNodeFactory) -> None:
        for content in factory.group_docs(self.file):
            self._groups.append(content)

    def _add_annotation_docs(self, factory: DocsNodeFactory) -> None:
        for content in factory.annotation_docs(self.file):
            self._annotations.append(content)

    def section_doc(self, section: DocSection) -> Optional[GroupsSectionDocs[IDynamoFile]]:
        for docs in self._groups:
            if docs.section != section:
                continue
            return docs
        return None

    def _get_nodes(self, section: DocSection) -> List[IModelWithId]:
        return [doc.linked_node() for doc in self._annotations if doc.section == section]

    def warning_nodes(self) -> List[IModelWithId]:
        return self._get_nodes(WARNINGS)

    def node_docs(self, model: IModelWithId) -> Optional[IDocContent[IDynamoFile]]:
        for docs in self._annotations:
            node = docs.linked_node()
            if model.node_id != node.node_id:
                continue
            return docs
        return None
