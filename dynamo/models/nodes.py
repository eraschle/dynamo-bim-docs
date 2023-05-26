from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from dynamo.models import model
from dynamo.models.model import (IAnnotation, IBaseModel, ICustomNode,
                                 IDependency, IGroup, IModelWithId, INode,
                                 IPackage)


@dataclass
class ABaseModel(IBaseModel):
    name: str = field(repr=True, compare=False)


@dataclass
class ABaseNode(ABaseModel):
    node_id: str = field(repr=False, compare=True)
    x: float = field(compare=False, repr=False)
    y: float = field(compare=False, repr=False)


@dataclass
class Annotation(ABaseNode, IAnnotation):
    description: str = field(repr=True, compare=False)
    name: str = field(default='Annotation', repr=True, compare=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)


@dataclass
class Group(ABaseNode, IGroup):
    color: str = field(compare=False, repr=False)
    description: str = field(compare=False, repr=False)
    node_ids: List[str] = field(compare=False, repr=False)
    _nodes: List[ABaseNode] = field(default_factory=list, compare=False, repr=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)

    @property
    def nodes(self) -> List[ABaseNode]:
        return self._nodes

    def add_nodes(self, callback: Callable[[Iterable[str]], List[ABaseNode]]) -> None:
        self._nodes.clear()
        self._nodes.extend(callback(self.node_ids))
        model.add_to_nodes(self, self._nodes, ['group'])


@dataclass
class ElementResolving(ABaseModel, IBaseModel):
    namespace: str = field(compare=False, repr=False)
    library: str = field(compare=False, repr=False)


@dataclass
class AInputOutputNode(ABaseModel, IBaseModel):
    description: str = field(compare=False, repr=False)
    initial_values: str = field(compare=False, repr=False)


@dataclass
class DynamoNode(ABaseNode):
    description: str = field(repr=False, compare=False)
    disabled: bool = field(repr=False, compare=False)
    show_geometry: bool = field(repr=False, compare=False)


@dataclass
class GeneralNode(DynamoNode):
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)


@dataclass
class APathInputNode(DynamoNode, INode):
    hint_path: str = field(repr=False, compare=False)
    input_value: str = field(repr=False, compare=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)

    @property
    def path(self) -> Path:
        return Path(self.hint_path)


@dataclass
class FileInputNode(APathInputNode):
    pass


@dataclass
class DirInputNode(APathInputNode):
    pass


@dataclass
class CodeBlockNode(INode, DynamoNode):
    code: str = field(repr=False, compare=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)


@dataclass
class PythonCodeNode(INode, DynamoNode):
    code: str = field(repr=False, compare=False)
    engine: str = field(repr=False, compare=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)


def default_package() -> IPackage:
    return PackageDependency(name='', version='', node_ids=[])


@dataclass
class CustomNode(ICustomNode, INode, DynamoNode):
    uuid: str = field(compare=False, repr=True)
    package: IPackage = field(default_factory=default_package, compare=False, repr=True)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)


@dataclass
class CustomPythonNode(CustomNode):
    pass


@dataclass
class CustomNetNode(CustomNode):
    pass


@dataclass
class PackageDependency(IPackage, ABaseModel, IDependency[CustomNode]):
    version: str = field(repr=True, compare=False)
    node_ids: List[str] = field(default_factory=list, compare=False, repr=False)
    _nodes: List[CustomNode] = field(default_factory=list, compare=False, repr=False)

    @ property
    def full_name(self) -> str:
        return f'{self.name} [{self.version}]'

    @property
    def nodes(self) -> List[CustomNode]:
        return self._nodes

    def add_nodes(self, callback: Callable[[Iterable[str]], List[CustomNode]]) -> None:
        self._nodes.clear()
        self._nodes.extend(callback(self.node_ids))
        model.add_to_nodes(self, self._nodes, ['package'])


@dataclass
class ExternalDependency(ABaseModel, IDependency[IModelWithId]):
    node_ids: List[str] = field(default_factory=list, compare=False, repr=False)
    _nodes: List[INode] = field(default_factory=list, compare=False, repr=False)

    @property
    def nodes(self) -> List[INode]:
        return self._nodes

    def add_nodes(self, callback: Callable[[Iterable[str]], List[INode]]) -> None:
        self._nodes.clear()
        self._nodes.extend(callback(self.node_ids))
        model.add_to_nodes(self, self._nodes, [])
