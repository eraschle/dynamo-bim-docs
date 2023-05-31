from typing import Dict, Generic, List, Optional, TypeVar

from dynamo.docs.docs import IModelDocs
from dynamo.docs.models.content import IDocContent
from dynamo.models.model import IAnnotation, IDynamoFile, IModelWithId

from .models import (AnnotationDocs, DocSection, DocsParser, GroupsDocs,
                     SectionDocs)

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
        self._groups: Dict[DocSection, List[SectionDocs[IDynamoFile]]] = {}
        self._add_group_docs(factory)
        self._annotations: List[AnnotationDocs[IDynamoFile]] = []
        self._add_annotation_docs(factory)

    def _add_group_docs(self, factory: DocsNodeFactory) -> None:
        for content in factory.group_docs(self.file):
            section = content.section
            if section not in self._groups:
                self._groups[section] = []
            self._groups[section].append(content)

    def _add_annotation_docs(self, factory: DocsNodeFactory) -> None:
        for content in factory.annotation_docs(self.file):
            self._annotations.append(content)

    def section_doc(self, section: DocSection) -> List[SectionDocs[IDynamoFile]]:
        return self._groups.get(section, [])

    def node_docs(self, model: IModelWithId) -> Optional[IDocContent[IDynamoFile]]:
        for doc in self._annotations:
            node_doc = doc.linked_node()
            if model.node_id != node_doc.node_id:
                continue
            return doc
        return None
