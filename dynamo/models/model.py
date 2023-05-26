
from pathlib import Path
from typing import (Any, Callable, Iterable, List, Optional, Protocol, Type,
                    TypeVar, runtime_checkable)


@runtime_checkable
class IBaseModel(Protocol):
    name: str


class IModelWithId(IBaseModel, Protocol):
    node_id: str
    x: float
    y: float
    group: Optional['IGroup']


TNode = TypeVar('TNode', bound=IModelWithId)


class IModelWithNodes(Protocol[TNode]):
    node_ids: List[str]

    @property
    def nodes(self) -> List[TNode]:
        ...

    def add_nodes(self, callback: Callable[[Iterable[str]], List[TNode]]) -> None:
        ...


@runtime_checkable
class IAnnotation(IModelWithId, Protocol):
    description: str


@runtime_checkable
class IGroup(IAnnotation, IModelWithNodes[IModelWithId],  Protocol):
    color: str


class IDependency(IBaseModel, IModelWithNodes[TNode],  Protocol[TNode]):
    nodes: List[IBaseModel]


class IPackage(IBaseModel, Protocol):
    version: str

    @ property
    def full_name(self) -> str:
        ...


class INode(IModelWithId, Protocol):
    description: str
    disabled: bool
    show_geometry: bool


class ICustomNode(IBaseModel, Protocol):
    uuid: str
    name: str
    package: IPackage


class IInfoModel:
    version: str


TInfo = TypeVar('TInfo', bound=IInfoModel)
TFileNode = TypeVar('TFileNode', IModelWithId, ICustomNode)


class IFileModel(IBaseModel, Protocol[TFileNode, TInfo]):
    path: Path
    info: TInfo
    description: str
    nodes: List[TFileNode]

    @ property
    def full_name(self) -> str:
        ...

    def update_nodes(self) -> None:
        ...


TDependency = TypeVar('TDependency', bound=IDependency)


class IDynamoFile(IFileModel[INode, TInfo], Protocol[TInfo]):
    uuid: str
    groups: List[IGroup]
    annotations: List[IAnnotation]
    dependencies: List[IDependency]

    def has_dependencies(self, node_type: Type[TDependency]) -> bool:
        ...

    def get_dependencies(self, node_type: Type[TDependency]) -> List[TDependency]:
        ...

    def has_nodes(self, node_type: Type[TNode]) -> bool:
        ...

    def get_nodes(self, node_type: Type[TNode]) -> List[TNode]:
        ...


def add_to_nodes(parent: Any, nodes: List[Any], attr_names: Iterable[str]) -> None:
    for node in nodes:
        for attr in attr_names:
            setattr(node, attr, parent)
