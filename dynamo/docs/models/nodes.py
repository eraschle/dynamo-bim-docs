import inspect
import sys
from abc import abstractmethod
from typing import List, TypeVar

from dynamo.docs.manual.repository import DocsNodeRepository
from dynamo.docs.models.content import AHeadlineContent, IDocContent
from dynamo.models.model import IDynamoFile, IModelWithId, INode
from dynamo.models.nodes import (APathNode, CodeBlockNode, CustomNode, DynamoNode,
                                 ExternalDependency, InputCoreNode, InputOutputNode,
                                 PackageDependency, PythonCodeNode,
                                 SelectionNode)
from dynamo.utils import checks

TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class ANodeDocsContent(AHeadlineContent[TDynamoFile]):

    @classmethod
    @abstractmethod
    def is_node(cls, node: INode) -> bool:
        pass

    def __init__(self, file_docs: DocsNodeRepository[TDynamoFile], children: List[IDocContent[TDynamoFile]]) -> None:
        super().__init__(file=file_docs.file, children=children)
        self.file_docs = file_docs

    def _headline(self, level: int, **kwargs) -> List[str]:
        node = self._get_node(IModelWithId, **kwargs)
        return self.exporter.heading(node.name, level)

    def _table_lines(self, **kwargs) -> List[List[str]]:
        values = self.value_handler
        node = self._get_node(INode, **kwargs)
        group_name = None if node.group is None else node.group.name
        return [
            ['Beschreibung', values.as_str(node.description, default='Keine Beschreibung')],
            ['Gruppe', values.as_str(group_name, default='Keine Gruppe')],
            # [
            #     'Aktiviert', *values.bool_as_str(not node.disabled)
            # ],
            # [
            #     'Zeigt Geometrie', *values.bool_as_str(node.show_geometry)
            # ],
        ]

    def _information_table(self, **kwargs) -> List[str]:
        return self.exporter.as_table(["Attribut", "Wert"], self._table_lines(**kwargs))

    def _clean_existing_content(self) -> List[str]:
        lines = super()._clean_existing_content()
        table_ranges = self.exporter.table_ranges(lines)
        if len(table_ranges) == 0:
            return lines
        start, end = table_ranges[0]
        for _ in range(start, end):
            del lines[0]
        return lines

    @abstractmethod
    def _no_docs_content(self, **kwargs) -> List[str]:
        pass

    def _docs_content(self, level: int, **kwargs) -> List[str]:
        node = self._get_node(IModelWithId, **kwargs)
        node_docs = self.file_docs.node_docs(node)
        lines = self.exporter.empty_line()
        if node_docs is None:
            lines.extend(self._no_docs_content(**kwargs))
        else:
            lines.extend(node_docs.content(level, **kwargs))
        return lines

    def _headline_content(self, **kwargs) -> List[str]:
        lines = []
        lines.extend(self._get_lines(self._information_table, ** kwargs))
        content = self._get_lines(self._docs_content, strip_cb=self._strip_empty, **kwargs)
        if self._is_content(content):
            lines.extend(self.exporter.empty_line())
            lines.extend(content)
        return lines


class GeneralNodeDoc(ANodeDocsContent[TDynamoFile]):

    @classmethod
    def is_node(cls, node: INode) -> bool:
        return isinstance(node, DynamoNode)

    def _no_docs_content(self, **_) -> List[str]:
        return self.exporter.empty_line()


class SelectionNodeDoc(ANodeDocsContent[TDynamoFile]):

    @classmethod
    def is_node(cls, node: INode) -> bool:
        return isinstance(node, SelectionNode)

    def _table_lines(self, **kwargs) -> List[List[str]]:
        lines = super()._table_lines(**kwargs)
        node = self._get_node(SelectionNode, **kwargs)
        lines.append(['Selected', self.value_handler.as_str(
            node.selected, 'Kein Element selektiert')]
        )
        return lines

    def _no_docs_content(self, **_) -> List[str]:
        return self.exporter.empty_line()


class InputNodeDoc(ANodeDocsContent[TDynamoFile]):

    @classmethod
    def is_node(cls, node: INode) -> bool:
        return isinstance(node, InputCoreNode)

    def _table_lines(self, **kwargs) -> List[List[str]]:
        lines = super()._table_lines(**kwargs)
        node = self._get_node(InputCoreNode, **kwargs)
        lines.append([
            'Selected', self.value_handler.as_str(node.value, 'Keine Angaben')
        ])
        return lines

    def _no_docs_content(self, **_) -> List[str]:
        return self.exporter.empty_line()


class ACodeNodeDoc(ANodeDocsContent[TDynamoFile]):

    def _no_docs_content(self, **_) -> List[str]:
        return self.exporter.empty_line()

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


class CodeBlockDoc(ACodeNodeDoc[TDynamoFile]):

    @classmethod
    def is_node(cls, node: INode) -> bool:
        return isinstance(node, CodeBlockNode)

    def _code(self, **kwargs) -> str:
        node = self._get_node(CodeBlockNode, **kwargs)
        return node.code

    def _language(self) -> str:
        return 'DesignScript'


class PythonNodeDoc(ACodeNodeDoc[TDynamoFile]):

    @classmethod
    def is_node(cls, node: INode) -> bool:
        return isinstance(node, PythonCodeNode)

    def _table_lines(self, **kwargs) -> List[List[str]]:
        lines = super()._table_lines(**kwargs)
        node = self._get_node(PythonCodeNode, **kwargs)
        lines.append(['Engine', self.value_handler.as_str(node.engine, 'Keine Python Engine')])
        return lines

    def _code(self, **kwargs) -> str:
        node = self._get_node(PythonCodeNode, **kwargs)
        return node.code

    def _language(self) -> str:
        return 'python'


class PackageDependencyDocs(ANodeDocsContent[TDynamoFile]):

    @classmethod
    def is_node(cls, node: INode) -> bool:
        return isinstance(node, PackageDependency)

    def _headline(self, level: int, **kwargs) -> List[str]:
        package = self._get_node(PackageDependency, **kwargs)
        return self.exporter.heading(package.full_name, level)

    def _get_package_nodes(self, **kwargs) -> List[CustomNode]:
        package = self._get_node(PackageDependency, **kwargs)
        return package.nodes

    def _unique_package_nodes(self, **kwargs) -> List[CustomNode]:
        unique_nodes = {}
        for node in self._get_package_nodes(**kwargs):
            unique_name = f'{node.name}-{node.uuid}'
            if unique_name in unique_nodes:
                continue
            unique_nodes[unique_name] = node
        return sorted(unique_nodes.values(), key=lambda node: node.name)

    def _custom_node_name(self, node: CustomNode) -> str:
        node_doc = self.manager.doc_file_of(node)
        if node_doc is None:
            return node.name
        return self.exporter.file_link(node_doc, self.file)

    def _node_line(self, node: CustomNode) -> List[str]:
        node_name = self._custom_node_name(node)
        return [node_name, node.uuid]

    def _headline_content(self, **kwargs) -> List[str]:
        unique_nodes = self._unique_package_nodes(**kwargs)
        table_lines = [self._node_line(node) for node in unique_nodes]
        return self.exporter.as_table(["Name", "UUID"], table_lines)

    def _no_docs_content(self, **_) -> List[str]:
        return self.exporter.empty_line()


class ExternalDependencyDocs(ANodeDocsContent[TDynamoFile]):

    @classmethod
    def is_node(cls, node: INode) -> bool:
        return isinstance(node, ExternalDependency)

    def _dependency_name(self, node: INode) -> str:
        if not isinstance(node, APathNode):
            return node.name
        return node.path.name

    def _headline_content(self, **kwargs) -> List[str]:
        external = self._get_node(ExternalDependency, **kwargs)
        if checks.is_blank(external.nodes):
            return ['Keine Nodes']
        lines = [self._dependency_name(node) for node in external.nodes]
        return self.exporter.as_list(lines)

    def _no_docs_content(self, **_) -> List[str]:
        return self.exporter.empty_line()


class AInOutputNodeDocs(ANodeDocsContent[TDynamoFile]):

    def _table_lines(self, **kwargs) -> List[List[str]]:
        node = self._get_node(InputOutputNode, **kwargs)
        lines = super()._table_lines(**kwargs)
        if self._has_value(node):
            lines.append(['Wert', self._get_value(node)])
        return lines

    def _is_boolean(self, node: InputOutputNode) -> bool:
        if node.value_type.lower() not in ('boolean', 'bool'):
            return False
        try:
            bool(node.value)
            return True
        except ValueError:
            return False

    def _get_bool_value(self, node: InputOutputNode) -> str:
        return self.value_handler.bool_as_str(bool(node.value))

    @abstractmethod
    def _has_value(self, node: InputOutputNode) -> bool:
        pass

    @abstractmethod
    def _get_value(self, node: InputOutputNode) -> str:
        pass

    def _no_docs_content(self, **_) -> List[str]:
        return self.value_handler.as_list('Keine Beschreibung vorhanden')


class InputNodeDocs(AInOutputNodeDocs):

    @classmethod
    def is_node(cls, node: INode) -> bool:
        return isinstance(node, InputOutputNode)

    def _has_value(self, node: InputOutputNode) -> bool:
        return True

    def _get_value(self, node: InputOutputNode) -> str:
        if self._is_boolean(node):
            return self._get_bool_value(node)
        return self.value_handler.as_str(node.value, "Kein Angaben")


class OutputNodeDocs(AInOutputNodeDocs):

    @classmethod
    def is_node(cls, node: INode) -> bool:
        return isinstance(node, InputOutputNode)

    def _has_value(self, node: InputOutputNode) -> bool:
        return len(node.value) > 0

    def _get_value(self, node: InputOutputNode) -> str:
        if self._is_boolean(node):
            return self._get_bool_value(node)
        return self.value_handler.as_str(node.value, "Kein Angabe")


def all_node_docs(docs: DocsNodeRepository[TDynamoFile]) -> List[IDocContent[TDynamoFile]]:
    classes = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    instances = []
    for _, clazz in classes:
        if not issubclass(clazz, ANodeDocsContent) or clazz == GeneralNodeDoc or inspect.isabstract(clazz):
            continue
        inst = clazz(docs, children=[])
        instances.append(inst)
    return instances


def general_node_docs(docs: DocsNodeRepository[TDynamoFile]) -> IDocContent[TDynamoFile]:
    return GeneralNodeDoc(docs, children=[])
