from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol, TypeVar

from dynamo.models.files import CustomFileNode, Package, Script
from dynamo.models.nodes import CustomNode

TModel = TypeVar('TModel', covariant=True)
TContent = TypeVar('TContent', contravariant=True)


class IBuilder(Protocol[TModel, TContent]):

    def can_build(self, content: TContent, **kwargs) -> bool:
        ...

    def build(self, content: TContent, **kwargs) -> TModel:
        ...


TSource = TypeVar('TSource', covariant=False)


class ISourceRepository(Protocol[TSource]):
    file_path: Path
    content: TSource

    def can_read(self, path: Path):
        """Return True if the path can be read, otherwise False"""
        ...

    def read(self, path: Path):
        """Read and store the content of file path."""
        ...

    def ger_value(self, key: str, default: Any) -> Any:
        """Read and store the content of file path."""
        ...

    def nodes(self) -> List[Dict[str, Any]]:
        """Return all node information as a list of dictionaries"""
        ...

    def groups(self) -> List[Dict[str, Any]]:
        """Return all annotations."""
        ...

    def dependencies(self) -> List[Dict[str, Any]]:
        """Return all package dependencies."""
        ...

    def annotations(self) -> List[Dict[str, Any]]:
        """Return all annotations (Bemerkungen)."""
        ...

    def dynamo_info(self) -> Dict[str, Any]:
        ...

    def package_info(self) -> Dict[str, Any]:
        ...


class IDynamoFactory(Protocol):

    def can_create(self, path: Path) -> bool:
        ...

    def script(self, path: Path) -> Script:
        ...

    def package(self, path: Path) -> Package:
        ...

    def custom_node(self, path: Path) -> List[CustomFileNode]:
        ...


class INodeRepository(Protocol):

    def add(self, package: Package):
        ...

    def get(self, node: CustomNode) -> Optional[CustomFileNode]:
        ...


class INodeGateway(Protocol):
    repository: INodeRepository

    def scripts(self, paths: Iterable[Path]) -> List[Script]:
        ...

    def packages(self, paths: Iterable[Path]) -> List[Package]:
        ...

    def documentations(self, paths: Iterable[Path]) -> List[Path]:
        ...

    def html_documentations(self, paths: Iterable[Path]) -> List[Path]:
        ...
