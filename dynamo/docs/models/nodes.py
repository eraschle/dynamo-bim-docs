from abc import abstractmethod
from typing import List, TypeVar

from dynamo.docs.docs import IModelDocs
from dynamo.docs.manual.parser import DocsNodeRepository
from dynamo.docs.models.content import (AHeadlineContent, AHeadlineDoc,
                                        IDocContent)
from dynamo.models.model import IBaseModel, ICodeNode, IDynamoFile, INode
from dynamo.models.nodes import (APathInputNode, CodeBlockNode, CustomNode,
                                 ExternalDependency, PackageDependency,
                                 PythonCodeNode)
from dynamo.utils import checks

TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class ANodeDocsContent(AHeadlineContent[TDynamoFile]):

    def __init__(self, file_docs: DocsNodeRepository[TDynamoFile]) -> None:
        super().__init__(file=file_docs.file)
        self.file_docs = file_docs

    def _headline(self, level: int, **kwargs) -> List[str]:
        node = self._get_node(IBaseModel, **kwargs)
        return self.exporter.heading(node.name, level)

    def _information_table(self, node: INode) -> List[str]:
        values = self.value_handler
        group_name = None if node.group is None else node.group.name
        lines = [
            ['Beschreibung', values.as_str(node.description, default='Keine Beschreibung')],
            ['Gruppe', values.as_str(group_name, default='Keine Gruppe')],
            # [
            #     'Aktiviert', *values.bool_as_str(not node.disabled)
            # ],
            # [
            #     'Zeigt Geometrie', *values.bool_as_str(node.show_geometry)
            # ],
        ]
        if isinstance(node, PythonCodeNode):
            lines.append(['Engine', values.as_str(node.engine, 'Keine Python Engine')])
        return self.exporter.as_table(["Attribut", "Wert"], lines)

    def _headline_content(self, **kwargs) -> List[str]:
        node = self._get_node(INode, **kwargs)

        lines = []
        infos = self._information_table(node)
        lines.extend(self._strip_empty(infos))
        lines = self._rstrip_empty(lines)

        lines.extend(self.exporter.empty_line())
        docs = self._docs_content(**kwargs)
        lines.extend(self._strip_empty(docs))
        lines = self._rstrip_empty(lines)
        return lines

    def _docs_content(self, level: int, **kwargs) -> List[str]:
        node = self._get_node(INode, **kwargs)
        node_docs = self.file_docs.node_docs(node)
        if node_docs is None:
            return []
        return node_docs.content(level, **kwargs)


class ACodeNodeDoc(ANodeDocsContent[TDynamoFile]):

    def _headline_content(self, **kwargs) -> List[str]:
        lines = super()._headline_content(**kwargs)
        lines.extend(self.exporter.empty_line())
        code = self.exporter.as_code(
            self._code(**kwargs), self._language(), self._indent()
        )
        lines.extend(code)
        return self._rstrip_empty(lines)

    @abstractmethod
    def _code(self, **kwargs) -> str:
        pass

    @abstractmethod
    def _language(self) -> str:
        pass

    def _indent(self) -> int:
        return 4


class ACodeNodesDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 code_docs: IDocContent[TDynamoFile], headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.code_docs = code_docs

    def _headline_content(self, **_) -> List[str]:
        values = self.value_handler
        return values.default_if_empty(self._code_nodes(), self._no_nodes_msg())

    @ abstractmethod
    def _code_nodes(self) -> List[ICodeNode]:
        pass

    @ abstractmethod
    def _no_nodes_msg(self) -> str:
        pass

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for node in self._code_nodes():
            content = self._get_content(self.code_docs, level, node=node, **kwargs)
            lines.extend(content)
        return lines


class CodeBlockDoc(ACodeNodeDoc[TDynamoFile]):

    def _code(self, **kwargs) -> str:
        node = self._get_node(CodeBlockNode, **kwargs)
        return node.code

    def _language(self) -> str:
        return 'DesignScript'


class CodeBlocksDocs(ACodeNodesDocs[TDynamoFile]):

    def _code_nodes(self) -> List[ICodeNode]:
        return self.model.get_nodes(CodeBlockNode)

    def _no_nodes_msg(self) -> str:
        return 'Keine Code Blocks'


class PythonNodeDoc(ACodeNodeDoc[TDynamoFile]):

    def _code(self, **kwargs) -> str:
        node = self._get_node(PythonCodeNode, **kwargs)
        return node.code

    def _language(self) -> str:
        return 'python'


class PythonNodesDocs(ACodeNodesDocs[TDynamoFile]):

    def _code_nodes(self) -> List[ICodeNode]:
        return self.model.get_nodes(PythonCodeNode)

    def _no_nodes_msg(self) -> str:
        return 'Keine Python Nodes'


class SourceCodeDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 children: List[ACodeNodesDocs[TDynamoFile]], headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.children = children

    def _headline_content(self, **_) -> List[str]:
        return self.exporter.empty_line()

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_content(child, level, **kwargs)
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

    def _headline_content(self, **kwargs) -> List[str]:
        lines = super()._headline_content(**kwargs)
        lines.extend(self.exporter.empty_line())
        lines.extend(self._manual_docs())
        return lines


class PackageDependencyDocs(ANodeDocsContent[TDynamoFile]):

    def _package_name(self, node: CustomNode) -> str:
        doc_file = self.manager.doc_file_of(node)
        if doc_file is None:
            return node.name
        return self.exporter.file_link(doc_file, self.file)

    def _headline(self, level: int, **kwargs) -> List[str]:
        package = self._get_node(PackageDependency, **kwargs)
        return self.exporter.heading(package.full_name, level)

    def _headline_content(self, **kwargs) -> List[str]:
        package = self._get_node(PackageDependency, **kwargs)
        if checks.is_blank(package.nodes):
            return ['Keine Packages Nodes']
        lines = [[self._package_name(node), node.uuid] for node in package.nodes]
        return self.exporter.as_table(["Name", "UUID"], lines)


class PackageDependenciesDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 node_docs: IDocContent[TDynamoFile],
                 headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.node_docs = node_docs

    def _headline_content(self, **_) -> List[str]:
        values = self.value_handler
        packages = self.model.get_dependencies(PackageDependency)
        return values.default_if_empty(packages, 'Keine Abhängigkeiten zu Packages')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        packages = self.model.get_dependencies(PackageDependency)
        lines = super()._children_content(level, **kwargs)
        for package in packages:
            content = self._get_content(self.node_docs, level, node=package, **kwargs)
            lines.extend(content)
        return lines


class ExternalDependencyDocs(ANodeDocsContent[TDynamoFile]):

    def _dependency_name(self, node: INode) -> str:
        if not isinstance(node, APathInputNode):
            return node.name
        return node.path.name

    def _headline_content(self, **kwargs) -> List[str]:
        external = self._get_node(ExternalDependency, **kwargs)
        if checks.is_blank(external.nodes):
            return ['Keine Nodes']
        lines = [self._dependency_name(node) for node in external.nodes]
        return self.exporter.as_list(lines)


class ExternalDependenciesDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 node_docs: IDocContent[TDynamoFile], headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.node_docs = node_docs

    def _headline_content(self, **_) -> List[str]:
        values = self.value_handler
        externals = self.model.get_dependencies(ExternalDependency)
        return values.default_if_empty(externals, 'Keine Externen Abhängigkeiten')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        externals = self.model.get_dependencies(ExternalDependency)
        lines = super()._children_content(level, **kwargs)
        for external in externals:
            content = self._get_content(self.node_docs, level, node=external, **kwargs)
            lines.extend(content)
        return lines


class DependenciesDocs(AHeadlineDoc[TDynamoFile]):

    def __init__(self, file: IModelDocs[TDynamoFile],
                 children: List[IDocContent[TDynamoFile]], headline: str) -> None:
        super().__init__(file=file, headline=headline)
        self.children = children

    def _headline_content(self, **_) -> List[str]:
        return []

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_content(child, level, **kwargs)
            lines.extend(content)
        return lines
