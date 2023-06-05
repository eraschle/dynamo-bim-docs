from abc import abstractmethod
from typing import List, TypeVar

from dynamo.docs.manual.repository import DocsNodeRepository
from dynamo.docs.manual.sections import DESCRIPTION, DOCS, WARNINGS, DocSection
from dynamo.docs.models.content import AHeadlineContent, IDocContent
from dynamo.docs.models.nodes import ANodeDocsContent
from dynamo.models.model import IDynamoFile, IModelWithId, INode

TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class ASectionDoc(AHeadlineContent[TDynamoFile]):

    def __init__(self, section: DocSection, file_docs: DocsNodeRepository[TDynamoFile],
                 children: List[IDocContent[TDynamoFile]]) -> None:
        super().__init__(file=file_docs.file, children=children)
        self.section = section
        self.file_docs = file_docs

    def _headline(self, level: int, **_) -> List[str]:
        return self.exporter.heading(self.section.title, level)

    def _docs(self, level: int, **kwargs) -> List[str]:
        node_docs = self.file_docs.section_doc(self.section)
        lines = []
        if node_docs is not None:
            for docs in node_docs.children:
                content = self._get_lines(docs.content, self._strip_empty, level=level, **kwargs)
                if not self._is_content(content):
                    continue
                lines.extend(self.exporter.empty_line())
                lines.extend(content)
        if not self._is_content(lines):
            return self._no_docs_content(**kwargs)
        return lines

    @abstractmethod
    def _no_docs_content(self, **kwargs) -> List[str]:
        pass

    def _section_content(self, **kwargs) -> List[str]:
        return self.exporter.empty_line()

    def _headline_content(self, **kwargs) -> List[str]:
        lines = []
        section_content = self._get_lines(self._section_content, **kwargs)
        if self._is_content(section_content):
            lines.extend(section_content)
        doc_content = self._get_lines(self._docs, **kwargs)
        if self._is_content(doc_content):
            lines.extend(self.exporter.empty_line())
            lines.extend(doc_content)
        return lines

    # def _child_content(self, level: int, **kwargs) -> List[str]:
    #     lines = []
    #     for child in self.file_docs.section_doc(self.section):
    #         content = self._get_lines(child.content, level=level, **kwargs)
    #         lines.extend(content)
    #     return lines

    # def _headline_content(self, **kwargs) -> List[str]:
    #     level = self._get_level(**kwargs)
    #     section_docs = self.file_docs.section_doc(self.section)
    #     if checks.is_blank(section_docs):
    #         return self._manual_docs()
    #     lines = []
    #     for section_doc in section_docs:
    #         content = section_doc.content(level=level, **kwargs)
    #         lines.extend(content)
    #     return lines


class TutorialDocs(ASectionDoc[TDynamoFile]):

    def __init__(self, file_docs: DocsNodeRepository[TDynamoFile],
                 children: List[IDocContent[TDynamoFile]]) -> None:
        super().__init__(DOCS, file_docs, children)

    def _no_docs_content(self, **_) -> List[str]:
        return self.value_handler.as_list('Keine Anleitung vorhanden')


# class SolutionOrProblemDocs(ASectionDoc[TDynamoFile]):

#     def __init__(self, file_docs: DocsNodeRepository[TDynamoFile],
#                  children: List[IDocContent[TDynamoFile]]) -> None:
#         super().__init__(SOLUTION, file_docs, children)

#     def _no_docs_content(self, **_) -> List[str]:
#         return self.value_handler.as_list('Keine Beschreibung vorhanden')


class AFileDescriptionDocs(ASectionDoc[TDynamoFile]):

    def __init__(self, file_docs: DocsNodeRepository[TDynamoFile],
                 children: List[IDocContent[TDynamoFile]]) -> None:
        super().__init__(DESCRIPTION, file_docs, children)

    def _common_informations(self) -> List[List[str]]:
        return [
            ['UUID', self.value_handler.as_str(self.model.uuid)],
            ['Dynamo-Version', self.value_handler.as_str(self.model.info.version)],
        ]

    def _information_table(self) -> List[str]:
        return self.exporter.as_table(None, self._common_informations())

    def _section_content(self, **kwargs) -> List[str]:
        lines = self._information_table()
        description = self._get_lines(self._description, **kwargs)
        if self._is_content(description):
            lines.extend(self.exporter.empty_line())
            lines.extend(description)
        return lines

    @ abstractmethod
    def _description(self, **kwargs) -> List[str]:
        pass

    def _no_docs_content(self, **_) -> List[str]:
        return self.value_handler.as_list('Keine Beschreibung vorhanden')


class NodeWarningDocs(ANodeDocsContent[TDynamoFile]):

    @ classmethod
    def is_node(cls, node: INode) -> bool:
        return True

    def __init__(self, file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(file_docs, children=[])

    def _no_docs_content(self, **_) -> List[str]:
        return self.exporter.empty_line()


class NodeWarningSectionDocs(ASectionDoc[TDynamoFile]):

    def __init__(self, file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(WARNINGS, file_docs, children=[NodeWarningDocs(file_docs)])

    def _warning_nodes(self) -> List[IModelWithId]:
        return self.file_docs.warning_nodes()

    def has_content(self, **_) -> bool:
        return len(self._warning_nodes()) > 0

    def _headline_content(self, **_) -> List[str]:
        return self.exporter.empty_line()

    def _child_docs(self, **kwargs) -> List[str]:
        return self.children[0].content(**kwargs)

    def _child_content(self, level: int, **kwargs) -> List[str]:
        lines = []
        for external in self._warning_nodes():
            content = self._get_lines(self._child_docs, level=level, node=external, **kwargs)
            lines.extend(content)
        return lines

    def _no_docs_content(self, **_) -> List[str]:
        return self.exporter.empty_line()
