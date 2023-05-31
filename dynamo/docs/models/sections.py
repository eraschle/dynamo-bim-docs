from typing import List, TypeVar

from dynamo.docs.manual.models import DocSection
from dynamo.docs.manual.parser import DocsNodeRepository
from dynamo.docs.models.content import AHeadlineContent, IDocContent
from dynamo.models.files import CustomFileNode
from dynamo.models.model import IDynamoFile
from dynamo.models.nodes import APathInputNode, DirInputNode, FileInputNode

TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class ASectionDoc(AHeadlineContent[TDynamoFile]):

    def __init__(self, section: DocSection, file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(file=file_docs.file)
        self.section = section
        self.file_docs = file_docs

    def _headline(self, level: int, **_) -> List[str]:
        return self.exporter.heading(self.section.title, level)

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

    def __init__(self, section: DocSection,
                 children: List[IDocContent[TDynamoFile]],
                 file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(section, file_docs)
        self.children = children

    def _headline_content(self, **_) -> List[str]:
        return self._manual_docs()

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class SolutionOrProblemDocs(ASectionDoc[TDynamoFile]):

    def _headline_content(self, **_) -> List[str]:
        return self._manual_docs()

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.file_docs.section_doc(self.section):
            content = self._get_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class FileInformationDocs(ASectionDoc[TDynamoFile]):

    def __init__(self, children: List[IDocContent[TDynamoFile]],
                 section: DocSection, file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(section=section, file_docs=file_docs)
        self.children = children

    def _headline_content(self, **_) -> List[str]:
        lines = [
            ['UUID', self.value_handler.as_str(self.model.uuid)],
            ['Version', self.value_handler.as_str(self.model.info.version)],
        ]
        if isinstance(self.model, CustomFileNode):
            lines.append(
                ['Kategorie', self.value_handler.as_str(self.model.category)]
            )
        return self.exporter.as_table(["Attribut", "Wert"], lines)

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class FileDescriptionDocs(ASectionDoc[TDynamoFile]):

    def _headline_content(self, **_) -> List[str]:
        return self.value_handler.as_list(self.model.description, 'Keine Beschreibung')


class FilesAndDirectoriesDocs(ASectionDoc[TDynamoFile]):

    def __init__(self, node_docs: IDocContent[TDynamoFile],
                 section: DocSection, file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(section=section, file_docs=file_docs)
        self.node_docs = node_docs

    def _path_nodes(self) -> List[APathInputNode]:
        nodes = []
        nodes.extend(self.model.get_nodes(FileInputNode))
        nodes.extend(self.model.get_nodes(DirInputNode))
        return nodes

    def _headline_content(self, **_) -> List[str]:
        nodes = self._path_nodes()
        return self.value_handler.default_if_empty(nodes, 'Keine Pfad-Nodes')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        lines = []
        for node in self._path_nodes():
            content = self._get_content(self.node_docs, level, node=node, **kwargs)
            lines.extend(content)
        return lines
