from abc import abstractmethod
from ctypes import ArgumentError
from typing import List, Protocol, Type, TypeVar

from dynamo.docs.docs import IDocsManager, IExporter, IModelDocs, ValueHandler
from dynamo.models.files import CustomFileNode
from dynamo.models.model import IBaseModel, IDynamoFile, IFileModel, INode
from dynamo.models.nodes import (APathInputNode, CodeBlockNode, CustomNode,
                                 DirInputNode, ExternalDependency,
                                 FileInputNode, PackageDependency,
                                 PythonCodeNode)
from dynamo.utils import checks

TFile = TypeVar('TFile', bound=IFileModel)
TDynamo = TypeVar('TDynamo', bound=IDynamoFile)


class IDocContent(Protocol[TFile]):
    file: IModelDocs[TFile]

    @property
    def manager(self) -> IDocsManager:
        ...

    @property
    def exporter(self) -> IExporter:
        ...

    @property
    def values(self) -> ValueHandler:
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
    def values(self) -> ValueHandler:
        return self.exporter.values

    def _strip_empty(self, content: List[str]) -> List[str]:
        return self.values.strip_empty(content)

    def _lstrip_empty(self, content: List[str]) -> List[str]:
        return self.values.strip_starting_empty(content)

    def _rstrip_empty(self, content: List[str]) -> List[str]:
        return self.values.strip_ending_empty(content)

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

    def _get_doc_content(self, child: IDocContent[TFile], level: int, **kwargs) -> List[str]:
        content = child.content(level, **kwargs)
        content = self._rstrip_empty(content)
        return content

    def _children_content(self, level: int, **kwargs) -> List[str]:
        return []


TNode = TypeVar('TNode', bound=IBaseModel)


class AHeadingContent(ADocContent[TFile]):

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
        # lines.extend(self.values.remove_starting_and_ending_empty_lines(heading))
        lines.extend(heading)
        lines.extend(self.exporter.empty_line())
        content = self._heading_content(level=level, **kwargs)
        lines.extend(content)
        # lines.extend(self.values.remove_starting_and_ending_empty_lines(content))
        return lines

    @abstractmethod
    def _heading(self, level: int, **kwargs) -> List[str]:
        pass

    @abstractmethod
    def _heading_content(self, **kwargs) -> List[str]:
        pass

    def _heading_value(self, lines: List[str]) -> str:
        heading = self.values.strip_starting_empty(lines)
        if len(heading) < 1:
            raise ValueError(f'No Heading in {lines}')
        return heading[0]

    def _clean_existing_content(self) -> List[str]:
        lines = self._strip_empty(self._existing_content[1:])
        lines = self.values.remove_no_manual_docs(lines)
        return lines

    def _set_existing_content(self, heading_lines: List[str]) -> None:
        heading = self._heading_value(heading_lines)
        lines = []
        for line in self.file.existing_docs():
            if len(lines) == 0 and not line.startswith(heading):
                continue
            elif len(lines) > 0 and self.exporter.is_heading(line):
                break
            lines.append(line.rstrip())
        self._existing_content = lines

    def _manual_docs(self) -> List[str]:
        existing = self._clean_existing_content()
        existing = self._strip_empty(existing)
        return self.values.value_or_default(existing, self.values.no_manual_doc)


class AHeadingTextDocs(AHeadingContent[TFile]):

    def __init__(self, file: IModelDocs[TFile], heading: str) -> None:
        super().__init__(file)
        self.heading = heading

    def _heading(self, level: int, **_) -> List[str]:
        return self.exporter.heading(self.heading, level)

    @abstractmethod
    def _heading_content(self, **kwargs) -> List[str]:
        pass


class TitleDocContent(ADocContent[TFile]):

    def _content(self, _: int) -> List[str]:
        lines = []
        lines.extend(self.exporter.doc_head())
        lines.extend(self.exporter.empty_line())
        lines.extend(self.exporter.title(self.file))
        return lines


def title_docs(file: IModelDocs[TFile]) -> IDocContent[TFile]:
    return TitleDocContent(file)


class TutorialDocs(AHeadingTextDocs[TFile]):

    def __init__(self, file: IModelDocs[TFile],
                 children: List[IDocContent[TFile]],
                 heading: str) -> None:
        super().__init__(file, heading)
        self.children = children

    def _heading_content(self, **_) -> List[str]:
        return self._manual_docs()

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class SolutionOrProblemDocs(AHeadingTextDocs[TDynamo]):

    def _heading_content(self, **_) -> List[str]:
        return self._manual_docs()


class FileInformationDocs(AHeadingTextDocs[TDynamo]):

    def __init__(self, file: IModelDocs[TDynamo],
                 children: List[IDocContent[TDynamo]],
                 heading: str) -> None:
        super().__init__(file, heading)
        self.children = children

    def _heading_content(self, **_) -> List[str]:
        lines = [
            self.values.values_or_default(['UUID', self.model.uuid]),
            self.values.values_or_default(['Version', self.model.info.version]),
        ]
        if isinstance(self.model, CustomFileNode):
            lines.append(
                self.values.values_or_default(['Kategorie', self.model.category])
            )
        return self.exporter.as_table(["Attribut", "Wert"], lines)

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class FileDescriptionDocs(AHeadingTextDocs[TFile]):

    def _heading_content(self, **_) -> List[str]:
        return self.values.value_or_default(self.model.description, 'Keine Beschreibung')


class ANodeDocsContent(AHeadingContent[TFile]):

    def _heading(self, level: int, **kwargs) -> List[str]:
        node = self._get_node(IBaseModel, **kwargs)
        return self.exporter.heading(node.name, level)

    def _heading_content(self, **kwargs) -> List[str]:
        node = self._get_node(INode, **kwargs)
        group_name = None if node.group is None else node.group.name
        lines = [
            [
                'Beschreibung',
                *self.values.value_or_default(node.description, default='Keine Beschreibung')
            ],
            [
                'Gruppe',
                *self.values.value_or_default(group_name, default='Keine Gruppe')
            ],
            [
                'Aktiviert',
                *self.values.bool_as_str(not node.disabled)
            ],
            [
                'Zeigt Geometrie',
                *self.values.bool_as_str(node.show_geometry)
            ],
        ]
        if isinstance(node, PythonCodeNode):
            lines.append([
                'Engine',
                *self.values.value_or_default(node.engine, 'Keine Python Engine')
            ])
        return self.exporter.as_table(["Attribut", "Wert"], lines)


class PackageDependencyDocs(ANodeDocsContent[TDynamo]):

    def _package_name(self, node: CustomNode) -> str:
        doc_file = self.manager.doc_file_of(node)
        if doc_file is None:
            return node.name
        return self.exporter.file_link(doc_file, self.file)

    def _heading(self, level: int, **kwargs) -> List[str]:
        package = self._get_node(PackageDependency, **kwargs)
        return self.exporter.heading(package.full_name, level)

    def _heading_content(self, **kwargs) -> List[str]:
        package = self._get_node(PackageDependency, **kwargs)
        if checks.is_blank(package.nodes):
            return self.values.value_or_default(package.nodes, 'Keine Nodes')
        lines = [[self._package_name(node), node.uuid] for node in package.nodes]
        return self.exporter.as_table(["Name", "UUID"], lines)


class PackageDependenciesDocs(AHeadingTextDocs[TDynamo]):

    def __init__(self, file: IModelDocs[TDynamo],
                 node_docs: IDocContent[TDynamo], heading: str) -> None:
        super().__init__(file, heading)
        self.node_docs = node_docs

    def _heading_content(self, **_) -> List[str]:
        packages = self.model.get_dependencies(PackageDependency)
        return self.values.default_if_empty(packages, 'Keine Abhängigkeiten zu Packages')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        packages = self.model.get_dependencies(PackageDependency)
        lines = super()._children_content(level, **kwargs)
        for package in packages:
            content = self._get_doc_content(self.node_docs, level, node=package, **kwargs)
            lines.extend(content)
        return lines


class ExternalDependencyDocs(ANodeDocsContent[TDynamo]):

    def _dependency_name(self, node: INode) -> str:
        if not isinstance(node, APathInputNode):
            return node.name
        return node.path.name

    def _heading_content(self, **kwargs) -> List[str]:
        external = self._get_node(ExternalDependency, **kwargs)
        if checks.is_blank(external.nodes):
            return self.values.value_or_default(external.nodes, 'Keine Nodes')
        lines = [self._dependency_name(node) for node in external.nodes]
        return self.exporter.as_list(lines)


class ExternalDependenciesDocs(AHeadingTextDocs[TDynamo]):

    def __init__(self, file: IModelDocs[TDynamo],
                 node_docs: IDocContent[TDynamo], heading: str) -> None:
        super().__init__(file, heading)
        self.node_docs = node_docs

    def _heading_content(self, **_) -> List[str]:
        externals = self.model.get_dependencies(ExternalDependency)
        return self.values.value_or_default(externals, 'Keine Externen Abhängigkeiten')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        externals = self.model.get_dependencies(ExternalDependency)
        lines = super()._children_content(level, **kwargs)
        for external in externals:
            content = self._get_doc_content(self.node_docs, level, node=external, **kwargs)
            lines.extend(content)
        return lines


class DependenciesDocs(AHeadingTextDocs[TDynamo]):

    def __init__(self, file: IModelDocs[TDynamo],
                 children: List[IDocContent[TDynamo]], heading: str) -> None:
        super().__init__(file, heading)
        self.children = children

    def _heading_content(self, **_) -> List[str]:
        return []

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class CodeBlockDocs(ANodeDocsContent[TDynamo]):

    def _heading_content(self, **kwargs) -> List[str]:
        node = self._get_node(CodeBlockNode, **kwargs)
        lines = self.exporter.as_code(node.code, 'DesignScript', indent=4)
        return lines


class CodeBlocksDocs(AHeadingTextDocs[TDynamo]):

    def __init__(self, file: IModelDocs[TDynamo],
                 node_docs: IDocContent[TDynamo], heading: str) -> None:
        super().__init__(file, heading)
        self.node_docs = node_docs

    def _heading_content(self, **_) -> List[str]:
        code_blocks = self.model.get_nodes(CodeBlockNode)
        return self.values.default_if_empty(code_blocks, 'Keine Code Blocks')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        code_blocks = self.model.get_nodes(CodeBlockNode)
        lines = super()._children_content(level, **kwargs)
        for code_block in code_blocks:
            content = self._get_doc_content(self.node_docs, level, node=code_block, **kwargs)
            lines.extend(content)
        return lines


class PythonNodeDocs(ANodeDocsContent[TDynamo]):

    def _heading_content(self, **kwargs) -> List[str]:
        node = self._get_node(PythonCodeNode, **kwargs)
        lines = self.exporter.as_code(node.code, 'python', indent=4)
        return lines


class PythonNodesDocs(AHeadingTextDocs[TDynamo]):

    def __init__(self, file: IModelDocs[TDynamo],
                 node_docs: IDocContent[TDynamo], heading: str) -> None:
        super().__init__(file, heading)
        self.node_docs = node_docs

    def _heading_content(self, **_) -> List[str]:
        python_codes = self.model.get_nodes(PythonCodeNode)
        return self.values.default_if_empty(python_codes, 'Keine Python Nodes')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        python_nodes = self.model.get_nodes(PythonCodeNode)
        lines = super()._children_content(level, **kwargs)
        for python_node in python_nodes:
            content = self._get_doc_content(self.node_docs, level, node=python_node, **kwargs)
            lines.extend(content)
        return lines


class SourceCodeDocs(AHeadingTextDocs[TDynamo]):

    def __init__(self, file: IModelDocs[TDynamo],
                 children: List[IDocContent[TDynamo]], heading: str) -> None:
        super().__init__(file, heading)
        self.children = children

    def _heading_content(self, **_) -> List[str]:
        return []

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class FileAndDirectoryDocs(ANodeDocsContent[TDynamo]):

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


class FilesAndDirectoriesDocs(AHeadingTextDocs[TDynamo]):

    def __init__(self, file: IModelDocs[TDynamo],
                 node_docs: IDocContent[TDynamo],
                 heading: str) -> None:
        super().__init__(file, heading)
        self.node_docs = node_docs

    def _path_nodes(self) -> List[APathInputNode]:
        nodes = []
        nodes.extend(self.model.get_nodes(FileInputNode))
        nodes.extend(self.model.get_nodes(DirInputNode))
        return nodes

    def _heading_content(self, **_) -> List[str]:
        nodes = self._path_nodes()
        return self.values.default_if_empty(nodes, 'Keine Pfad-Nodes')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        lines = []
        for node in self._path_nodes():
            content = self._get_doc_content(self.node_docs, level, node=node, **kwargs)
            lines.extend(content)
        return lines
