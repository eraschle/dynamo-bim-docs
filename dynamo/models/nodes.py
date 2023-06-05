from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Any

from dynamo.models import model
from dynamo.models.model import (IAnnotation, IBaseModel, ICodeNode,
                                 ICustomNode, IDependency, IGroup,
                                 IModelWithId, INode, IPackage)


@dataclass
class ABaseModel(IBaseModel):
    name: str = field(repr=True, compare=False)


@dataclass
class ABaseNode(ABaseModel):
    node_id: str = field(repr=False, compare=True)
    x: float = field(compare=False, repr=False)
    y: float = field(compare=False, repr=False)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IModelWithId):
            return False
        return self.node_id == other.node_id


@dataclass
class Annotation(IAnnotation):
    node_id: str = field(repr=False, compare=True)
    name: str = field(repr=True, compare=False)
    x: float = field(compare=False, repr=False)
    y: float = field(compare=False, repr=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IModelWithId):
            return False
        return self.node_id == other.node_id


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
class DynamoNode(ABaseNode):
    description: str = field(repr=False, compare=False)
    disabled: bool = field(repr=False, compare=False)
    show_geometry: bool = field(repr=False, compare=False)
    is_input: bool = field(repr=False, compare=False)
    is_output: bool = field(repr=False, compare=False)


@dataclass
class InputOutputNode(INode):
    node: INode
    value_type: str
    value: str

    @property
    def name(self) -> str:
        return self.node.name

    @name.setter
    def name(self, name: str) -> None:
        self.node.name = name

    @property
    def node_id(self) -> str:
        return self.node.node_id

    @node_id.setter
    def node_id(self, node_id: str) -> None:
        self.node.node_id = node_id

    @property
    def x(self) -> float:
        return self.node.x

    @x.setter
    def x(self, x: float) -> None:
        self.node.x = x

    @property
    def y(self) -> float:
        return self.node.y

    @y.setter
    def y(self, y: float) -> None:
        self.node.y = y

    @property
    def description(self) -> str:
        return self.node.description

    @description.setter
    def description(self, description: str) -> None:
        self.node.description = description

    @property
    def disabled(self) -> bool:
        return self.node.disabled

    @disabled.setter
    def disabled(self, disabled: bool) -> None:
        self.node.disabled = disabled

    @property
    def show_geometry(self) -> bool:
        return self.node.show_geometry

    @show_geometry.setter
    def show_geometry(self, show_geometry: bool) -> None:
        self.node.show_geometry = show_geometry

    @property
    def is_input(self) -> bool:
        return self.node.is_input

    @is_input.setter
    def is_input(self, is_input: bool) -> None:
        self.node.is_input = is_input

    @property
    def is_output(self) -> bool:
        return self.node.is_output

    @is_output.setter
    def is_output(self, is_output: bool) -> None:
        self.node.is_output = is_output

    @property
    def group(self) -> Optional[IGroup]:
        return self.node.group

    @group.setter
    def group(self, group: Optional[IGroup]) -> None:
        self.node.group = group

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (ABaseNode, InputOutputNode)):
            return False
        return self.node_id == other.node_id


@dataclass
class GeneralNode(DynamoNode, INode):
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)


@dataclass
class APathNode(DynamoNode, INode):
    hint_path: str = field(repr=False, compare=False)
    input_value: str = field(repr=False, compare=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)

    @ property
    def path(self) -> Path:
        return Path(self.hint_path)


@dataclass
class FilePathNode(APathNode):
    pass


@dataclass
class DirPathNode(APathNode):
    pass


@dataclass
class SelectionNode(DynamoNode, INode):
    selected: str = field(repr=False, compare=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)


@dataclass
class InputCoreNode(DynamoNode, INode):
    value: int | float | bool | str = field(repr=False, compare=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)


@dataclass
class CodeBlockNode(DynamoNode, ICodeNode):
    code: str = field(repr=False, compare=False)
    group: Optional[IGroup] = field(default=None, compare=False, repr=False)


@dataclass
class PythonCodeNode(DynamoNode, ICodeNode):
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

    @ property
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

    @ property
    def nodes(self) -> List[INode]:
        return self._nodes

    def add_nodes(self, callback: Callable[[Iterable[str]], List[INode]]) -> None:
        self._nodes.clear()
        self._nodes.extend(callback(self.node_ids))
        model.add_to_nodes(self, self._nodes, [])
