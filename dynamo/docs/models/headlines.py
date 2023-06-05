from abc import abstractmethod
from typing import List, TypeVar

from dynamo.docs.docs import IModelDocs
from dynamo.docs.models.content import AHeadlineContent, IDocContent, TFile
from dynamo.models.model import ICodeNode, IDynamoFile
from dynamo.models.nodes import (CodeBlockNode, ExternalDependency,
                                 PackageDependency, PythonCodeNode)

TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class AHeadlineDoc(AHeadlineContent[TFile]):

    def __init__(self, file: IModelDocs[TFile], children: List[IDocContent[TFile]], headline: str) -> None:
        super().__init__(file, children)
        self.headline = headline

    def _headline(self, level: int, **_) -> List[str]:
        return self.exporter.heading(self.headline, level)


class ACodeNodesDocs(AHeadlineDoc[TDynamoFile]):

    def has_content(self, **_) -> bool:
        return len(self._code_nodes()) > 0

    def _headline_content(self, **_) -> List[str]:
        return self.exporter.empty_line()

    @abstractmethod
    def _code_nodes(self) -> List[ICodeNode]:
        pass

    def _code_doc(self, **kwargs) -> List[str]:
        return self.children[0].content(**kwargs)

    def _child_content(self, level: int, **kwargs) -> List[str]:
        lines = []
        for node in self._code_nodes():
            lines.extend(
                self._get_lines(
                    self._code_doc, self._rstrip_empty, level=level, node=node, **kwargs
                )
            )
        return lines


class CodeBlocksDocs(ACodeNodesDocs[TDynamoFile]):

    def _code_nodes(self) -> List[ICodeNode]:
        return self.model.get_nodes(CodeBlockNode)


class PythonNodesDocs(ACodeNodesDocs[TDynamoFile]):

    def _code_nodes(self) -> List[ICodeNode]:
        return self.model.get_nodes(PythonCodeNode)


class SourceCodeDocs(AHeadlineDoc[TDynamoFile]):

    def has_content(self, **kwargs) -> bool:
        return any(child.has_content(**kwargs) for child in self.children)

    def _headline_content(self, **_) -> List[str]:
        return self.exporter.empty_line()


class PackageDependenciesDocs(AHeadlineDoc[TDynamoFile]):

    def _packages(self) -> List[PackageDependency]:
        return self.model.get_dependencies(PackageDependency)

    def has_content(self, **_) -> bool:
        return len(self._packages()) > 0

    def _headline_content(self, **_) -> List[str]:
        return self.exporter.empty_line()

    def _child_doc(self, **kwargs) -> List[str]:
        return self.children[0].content(**kwargs)

    def _child_content(self, level: int, **kwargs) -> List[str]:
        lines = []
        for package in self._packages():
            content = self._get_lines(self._child_doc, level=level, node=package, **kwargs)
            lines.extend(content)
        return lines


class ExternalDependenciesDocs(AHeadlineDoc[TDynamoFile]):

    def _externals(self) -> List[ExternalDependency]:
        return self.model.get_dependencies(ExternalDependency)

    def has_content(self, **_) -> bool:
        return len(self._externals()) > 0

    def _headline_content(self, **_) -> List[str]:
        return self.exporter.empty_line()

    def _child_docs(self, **kwargs) -> List[str]:
        return self.children[0].content(**kwargs)

    def _child_content(self, level: int, **kwargs) -> List[str]:
        lines = []
        for external in self._externals():
            content = self._get_lines(self._child_docs, level=level, node=external, **kwargs)
            lines.extend(content)
        return lines


class DependenciesDocs(AHeadlineDoc[TDynamoFile]):

    def has_content(self, **kwargs) -> bool:
        return any(child.has_content(**kwargs) for child in self.children)

    def _headline_content(self, **_) -> List[str]:
        return self.exporter.empty_line()
