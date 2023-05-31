from abc import abstractmethod
from ctypes import ArgumentError
from typing import List, Protocol, Type, TypeVar, Any

from dynamo.docs.docs import IDocsManager, IExporter, IModelDocs
from dynamo.docs.docs_parser import DocSection, DocsNodeRepository
from dynamo.models.files import CustomFileNode
from dynamo.models.model import IBaseModel, IDynamoFile, IFileModel, IModelWithId, INode
from dynamo.models.nodes import (APathInputNode, CodeBlockNode, CustomNode,
                                 DirInputNode, ExternalDependency,
                                 FileInputNode, PackageDependency,
                                 PythonCodeNode)
from dynamo.utils import checks
from dynamo.utils.values import IValueHandler

TFile = TypeVar('TFile', bound=IFileModel)


class IDocContent(Protocol[TFile]):
    file: IModelDocs[TFile]

    @property
    def manager(self) -> IDocsManager:
        ...

    @property
    def exporter(self) -> IExporter:
        ...

    @property
    def model(self) -> TFile:
        ...

    def content(self, level: int, **kwargs) -> List[str]:
        ...


class ADocContent(IDocContent[TFile]):
    def __init__(self, file: IModelDocs[TFile]) -> None:
        self.file = file

    @property
    def manager(self) -> IDocsManager:
        return self.file.manager

    @property
    def exporter(self) -> IExporter:
        return self.manager.exporter

    @property
    def value_handler(self) -> IValueHandler:
        return self.exporter.value_handler

    def _strip_empty(self, content: List[str]) -> List[str]:
        return self.value_handler.strip_empty(content)

    def _lstrip_empty(self, content: List[str]) -> List[str]:
        return self.value_handler.strip_starting_empty(content)

    def _rstrip_empty(self, content: List[str]) -> List[str]:
        return self.value_handler.strip_ending_empty(content)

    @property
    def model(self) -> TFile:
        return self.file.model

    def content(self, level: int, **kwargs) -> List[str]:
        lines = []
        lines.extend(self.exporter.empty_line())
        content = self._content(level, **kwargs)
        lines.extend(self._strip_empty(content))
        lines.extend(self.exporter.empty_line())
        children = self._children_content(level + 1)
        lines.extend(self._strip_empty(children))
        return lines

    @abstractmethod
    def _content(self, level: int, **kwargs) -> List[str]:
        pass

    def _get_doc_content(self, child: IDocContent[Any], level: int, **kwargs) -> List[str]:
        content = child.content(level, **kwargs)
        content = self._rstrip_empty(content)
        return content

    def _children_content(self, level: int, **kwargs) -> List[str]:
        return []


TNode = TypeVar('TNode', bound=IBaseModel)


class AHeadlineContent(ADocContent[TFile]):

    def __init__(self, file: IModelDocs[TFile]) -> None:
        super().__init__(file)
        self._existing_content: List[str] = []

    def _get_node(self, node_type: Type[TNode], **kwargs) -> TNode:
        arg = 'node'
        node = kwargs.get(arg, None)
        if node is None:
            raise ArgumentError(f'Argument "{arg}" is None or does not exists')
        if not isinstance(node, node_type):
            raise ArgumentError(f'Except "{node_type}" but got {type(node)}')
        return node

    def _get_level(self, **kwargs) -> int:
        arg = 'level'
        node = kwargs.get(arg, 0)
        if node < 1:
            raise ArgumentError(f'Argument "{arg}" is None or does not exists')
        return node

    def _content(self, level: int, **kwargs) -> List[str]:
        lines = []
        heading = self._heading(level, **kwargs)
        self._set_existing_content(heading)
        # lines.extend(self.exporter.remove_starting_and_ending_empty_lines(heading))
        lines.extend(heading)
        lines.extend(self.exporter.empty_line())
        content = self._heading_content(level=level, **kwargs)
        lines.extend(content)
        # lines.extend(self.exporter.remove_starting_and_ending_empty_lines(content))
        return lines

    @abstractmethod
    def _heading(self, level: int, **kwargs) -> List[str]:
        pass

    @abstractmethod
    def _heading_content(self, **kwargs) -> List[str]:
        pass

    def _heading_value(self, lines: List[str]) -> str:
        heading = self.value_handler.strip_starting_empty(lines)
        if len(heading) < 1:
            raise ValueError(f'No Heading in {lines}')
        return heading[0]

    def _clean_existing_content(self) -> List[str]:
        lines = self._strip_empty(self._existing_content[1:])
        lines = self.value_handler.remove_default_doc_value(lines)
        return lines

    def _set_existing_content(self, heading_lines: List[str]) -> None:
        heading = self._heading_value(heading_lines)
        for line in self.file.existing_docs():
            if len(self._existing_content) == 0 and not line.startswith(heading):
                continue
            elif self._is_next_heading(line):
                break
            self._existing_content.append(line.rstrip())

    def _is_next_heading(self, line: str) -> bool:
        return self.exporter.is_heading(line)

    def _manual_docs(self) -> List[str]:
        values = self.value_handler
        existing = self._clean_existing_content()
        existing = self._strip_empty(existing)
        return values.get_or_default(
            existing, values.default_docs
        )


class AHeadlineDoc(AHeadlineContent[TFile]):

    def __init__(self, file: IModelDocs[TFile], headline: str) -> None:
        super().__init__(file)
        self.headline = headline

    def _heading(self, level: int, **_) -> List[str]:
        return self.exporter.heading(self.headline, level)

    @abstractmethod
    def _heading_content(self, **kwargs) -> List[str]:
        pass


TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class ASectionDoc(AHeadlineContent[TDynamoFile]):

    def __init__(self, section: DocSection, file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(file=file_docs.file)
        self.section = section
        self.file_docs = file_docs

    def _heading(self, level: int, **_) -> List[str]:
        return self.exporter.heading(self.section.title, level)

    def _heading_content(self, **kwargs) -> List[str]:
        level = self._get_level(**kwargs)
        section_docs = self.file_docs.section_doc(self.section)
        if checks.is_blank(section_docs):
            return self._manual_docs()
        lines = []
        for section_doc in section_docs:
            content = section_doc.content(level=level, **kwargs)
            lines.extend(content)
        return lines


class TitleDocContent(ADocContent[TFile]):

    def _content(self, _: int) -> List[str]:
        lines = []
        lines.extend(self.exporter.doc_head())
        lines.extend(self.exporter.empty_line())
        lines.extend(self.exporter.title(self.file))
        return lines


def title_docs(file: IModelDocs[TFile]) -> IDocContent[TFile]:
    return TitleDocContent(file)


class TutorialDocs(ASectionDoc[TDynamoFile]):

    def __init__(self, section: DocSection,
                 children: List[IDocContent[TDynamoFile]],
                 file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(section, file_docs)
        self.children = children

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class SolutionOrProblemDocs(ASectionDoc[TDynamoFile]):

    def _heading_content(self, **_) -> List[str]:
        return self._manual_docs()

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.file_docs.section_doc(self.section):
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class FileInformationDocs(ASectionDoc[TDynamoFile]):

    def __init__(self, children: List[IDocContent[TDynamoFile]],
                 section: DocSection, file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(section=section, file_docs=file_docs)
        self.children = children

    def _heading_content(self, **_) -> List[str]:
        lines = [
            self.value_handler.list_or_default(['UUID', self.model.uuid]),
            self.value_handler.list_or_default(['Version', self.model.info.version]),
        ]
        if isinstance(self.model, CustomFileNode):
            lines.append(
                self.value_handler.list_or_default(['Kategorie', self.model.category])
            )
        return self.exporter.as_table(["Attribut", "Wert"], lines)

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class FileDescriptionDocs(ASectionDoc[TDynamoFile]):

    def _heading_content(self, **_) -> List[str]:
        return self.value_handler.get_or_default(self.model.description, 'Keine Beschreibung')


class ANodeDocsContent(AHeadlineContent[TDynamoFile]):

    def __init__(self, file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(file=file_docs.file)
        self.file_docs = file_docs

    def _heading(self, level: int, **kwargs) -> List[str]:
        node = self._get_node(IBaseModel, **kwargs)
        return self.exporter.heading(node.name, level)

    def _information_table(self, node: INode) -> List[str]:
        values = self.value_handler
        group_name = None if node.group is None else node.group.name
        lines = [
            [
                'Beschreibung', *values.get_or_default(node.description,
                                                       default='Keine Beschreibung')
            ],
            [
                'Gruppe', *values.get_or_default(group_name, default='Keine Gruppe')
            ],
            [
                'Aktiviert', *values.bool_as_str(not node.disabled)
            ],
            [
                'Zeigt Geometrie', *values.bool_as_str(node.show_geometry)
            ],
        ]
        if isinstance(node, PythonCodeNode):
            lines.append(
                [
                    'Engine', *values.get_or_default(node.engine, 'Keine Python Engine')
                ])
        return self.exporter.as_table(["Attribut", "Wert"], lines)

    def _heading_content(self, **kwargs) -> List[str]:
        node = self._get_node(INode, **kwargs)
        docs_lines = self._information_table(node)
        node_docs = self.file_docs.node_docs(node)
        if node_docs is None:
            return docs_lines
        level = self._get_level()
        docs_lines.extend(self.exporter.empty_line())
        docs_lines.extend(node_docs.content(level, **kwargs))
        return docs_lines


class PackageDependencyDocs(ANodeDocsContent[TDynamoFile]):

    def _package_name(self, node: CustomNode) -> str:
        doc_file = self.manager.doc_file_of(node)
        if doc_file is None:
            return node.name
        return self.exporter.file_link(doc_file, self.file)

    def _heading(self, level: int, **kwargs) -> List[str]:
        package = self._get_node(PackageDependency, **kwargs)
        return self.exporter.heading(package.full_name, level)

    def _heading_content(self, **kwargs) -> List[str]:
        values = self.value_handler
        package = self._get_node(PackageDependency, **kwargs)
        if checks.is_blank(package.nodes):
            return values.get_or_default(package.nodes, 'Keine Nodes')
        lines = [[self._package_name(node), node.uuid] for node in package.nodes]
        return self.exporter.as_table(["Name", "UUID"], lines)


class PackageDependenciesDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 node_docs: IDocContent[TDynamoFile],
                 headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.node_docs = node_docs

    def _heading_content(self, **_) -> List[str]:
        values = self.value_handler
        packages = self.model.get_dependencies(PackageDependency)
        return values.default_or_empty(packages, 'Keine Abhängigkeiten zu Packages')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        packages = self.model.get_dependencies(PackageDependency)
        lines = super()._children_content(level, **kwargs)
        for package in packages:
            content = self._get_doc_content(self.node_docs, level, node=package, **kwargs)
            lines.extend(content)
        return lines


class ExternalDependencyDocs(ANodeDocsContent[TDynamoFile]):

    def _dependency_name(self, node: INode) -> str:
        if not isinstance(node, APathInputNode):
            return node.name
        return node.path.name

    def _heading_content(self, **kwargs) -> List[str]:
        values = self.value_handler
        external = self._get_node(ExternalDependency, **kwargs)
        if checks.is_blank(external.nodes):
            return values.get_or_default(external.nodes, 'Keine Nodes')
        lines = [self._dependency_name(node) for node in external.nodes]
        return self.exporter.as_list(lines)


class ExternalDependenciesDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 node_docs: IDocContent[TDynamoFile], headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.node_docs = node_docs

    def _heading_content(self, **_) -> List[str]:
        values = self.value_handler
        externals = self.model.get_dependencies(ExternalDependency)
        return values.get_or_default(externals, 'Keine Externen Abhängigkeiten')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        externals = self.model.get_dependencies(ExternalDependency)
        lines = super()._children_content(level, **kwargs)
        for external in externals:
            content = self._get_doc_content(self.node_docs, level, node=external, **kwargs)
            lines.extend(content)
        return lines


class DependenciesDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 children: List[IDocContent[TDynamoFile]], headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.children = children

    def _heading_content(self, **_) -> List[str]:
        return []

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class CodeBlockDoc(ANodeDocsContent[TDynamoFile]):

    def _heading_content(self, **kwargs) -> List[str]:
        node = self._get_node(CodeBlockNode, **kwargs)
        lines = self.exporter.as_code(node.code, 'DesignScript', indent=4)
        return lines


class CodeBlocksDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 node_docs: IDocContent[TDynamoFile], headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.node_docs = node_docs

    def _heading_content(self, **_) -> List[str]:
        values = self.value_handler
        code_blocks = self.model.get_nodes(CodeBlockNode)
        return values.get_or_default(code_blocks, 'Keine Code Blocks')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        code_blocks = self.model.get_nodes(CodeBlockNode)
        lines = super()._children_content(level, **kwargs)
        for code_block in code_blocks:
            content = self._get_doc_content(self.node_docs, level, node=code_block, **kwargs)
            lines.extend(content)
        return lines


class PythonNodeDoc(ANodeDocsContent[TDynamoFile]):

    def _heading_content(self, **kwargs) -> List[str]:
        node = self._get_node(PythonCodeNode, **kwargs)
        lines = self.exporter.as_code(node.code, 'python', indent=4)
        return lines


class PythonNodesDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 node_doc: IDocContent[TDynamoFile], headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.node_doc = node_doc

    def _heading_content(self, **_) -> List[str]:
        python_codes = self.model.get_nodes(PythonCodeNode)
        return self.value_handler.get_or_default(python_codes, 'Keine Python Nodes')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        python_nodes = self.model.get_nodes(PythonCodeNode)
        lines = super()._children_content(level, **kwargs)
        for python_node in python_nodes:
            content = self._get_doc_content(self.node_doc, level, node=python_node, **kwargs)
            lines.extend(content)
        return lines


class SourceCodeDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 children: List[IDocContent[TDynamoFile]], headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.children = children

    def _heading_content(self, **_) -> List[str]:
        return []

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class FileAndDirectoryDocs(ANodeDocsContent[TDynamoFile]):

    def _clean_existing_content(self) -> List[str]:
        lines = super()._clean_existing_content()
        table_ranges = self.exporter.table_ranges(lines)
        if len(table_ranges) == 0:
            return lines
        start, end = table_ranges[0]
        for _ in range(start, end):
            del lines[0]
        return lines

    def _heading_content(self, **kwargs) -> List[str]:
        lines = super()._heading_content(**kwargs)
        lines.extend(self.exporter.empty_line())
        lines.extend(self._manual_docs())
        return lines


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

    def _heading_content(self, **_) -> List[str]:
        nodes = self._path_nodes()
        return self.value_handler.default_or_empty(nodes, 'Keine Pfad-Nodes')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        lines = []
        for node in self._path_nodes():
            content = self._get_doc_content(self.node_docs, level, node=node, **kwargs)
            lines.extend(content)
        return lines
