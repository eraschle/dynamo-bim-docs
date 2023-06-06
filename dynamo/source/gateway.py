from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol, TypeVar

from dynamo.models.files import CustomFileNode, Package, PythonCustomFileNode, Script
from dynamo.models.model import IDynamoFile, IFileModel
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

    def can_read(self, path: Path) -> bool:
        """Return True if the path can be read, otherwise False"""
        ...

    def read(self, path: Path) -> None:
        """Read and store the content of file path."""
        ...

    def write(self, path: Path, content: TSource) -> None:
        """Write the content to the file"""
        ...

    def get_value(self, key: str, default: Any) -> Any:
        """Read and store the content of file path."""
        ...

    def nodes(self) -> List[Dict[str, Any]]:
        """Return nodes information as a list of dictionaries"""
        ...

    def inputs(self) -> List[Dict[str, Any]]:
        """Return input nodes as a list of dictionaries"""
        ...

    def outputs(self) -> List[Dict[str, Any]]:
        """Return output nodes as a list of dictionaries"""
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


TFileModel = TypeVar('TFileModel', bound=IFileModel)


class IFileBuilder(IBuilder[TFileModel, TContent], Protocol[TFileModel, TContent]):

    def change_name(self, node: TFileModel, content: TContent, new_name: str) -> TFileModel:
        ...

    def change_uuid(self, node: TFileModel, content: TContent, new_uuid: str) -> TFileModel:
        ...


TFileContent = TypeVar('TFileContent')


class IDynamoFactory(Protocol[TFileContent]):
    script_builder: IFileBuilder[Script, TFileContent
                                 ]
    custom_node_builder: IFileBuilder[PythonCustomFileNode, TFileContent]
    repository: ISourceRepository[TFileContent]

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


TDynamoFile = TypeVar('TDynamoFile', bound=IDynamoFile)


class INodeGateway(Protocol):
    repository: INodeRepository
    scripts: List[Script]
    packages: List[Package]

    def change_name(self, node: TDynamoFile, new_name: str) -> TDynamoFile:
        ...

    def change_uuid(self, node: TDynamoFile, new_uuid: str) -> TDynamoFile:
        ...

    def read_scripts(self, paths: Iterable[Path]) -> List[Script]:
        ...

    def read_packages(self, paths: Iterable[Path]) -> List[Package]:
        ...

    def documentations(self, paths: Iterable[Path]) -> List[Path]:
        ...

    def html_documentations(self, paths: Iterable[Path]) -> List[Path]:
        ...
