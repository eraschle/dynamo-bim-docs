import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Type

from dynamo.models.nodes import CustomNode, InputOutputNode, PackageDependency

from . import model
from .model import (IAnnotation, IBaseModel, ICustomNode, IDependency,
                    IDynamoFile, IFileModel, IGroup, IInfoModel, IModelWithId,
                    INode, IPackage, TDependency, TNode)

log = logging.getLogger(__name__)


@dataclass
class AFileBaseModel(IBaseModel):
    path: Path = field(compare=True, repr=False)
    name: str = field(compare=False, repr=True)
    description: str = field(compare=False, repr=False)


@dataclass
class DynamoInfo(IInfoModel):
    version: str = field(compare=False, repr=False)
    scale_factor: str = field(compare=False, repr=False)
    has_run_without_crash: bool = field(compare=False, repr=False)
    is_visible_in_library: bool = field(compare=False, repr=False)
    run_type: str = field(compare=False, repr=False)


def _node_by_id(node_id: str, nodes: Iterable[TNode]) -> Optional[TNode]:
    for node in nodes:
        if node.node_id != node_id:
            continue
        return node
    return None


def _nodes_by_ids(node_ids: Iterable[str], nodes: Iterable[TNode]) -> List[TNode]:
    nodes_with_ids = [_node_by_id(node_id, nodes) for node_id in node_ids]
    return [node for node in nodes_with_ids if node is not None]


@dataclass
class ADynamoFileNode(AFileBaseModel, IDynamoFile[DynamoInfo]):
    uuid: str = field(compare=False, repr=True)
    info: DynamoInfo = field(compare=False, repr=False)
    nodes: List[INode] = field(compare=False, repr=False)
    groups: List[IGroup] = field(compare=False, repr=False)
    dependencies: List[IDependency] = field(compare=False, repr=False)
    annotations: List[IAnnotation] = field(compare=False, repr=False)

    @property
    def full_name(self) -> str:
        return f'{self.name} [{self.uuid}]'

    @property
    def version(self) -> str:
        return self.info.version

    def _update_group_in_nodes(self, node_ids: Iterable[str]) -> List[IModelWithId]:
        nodes: List[IModelWithId] = _nodes_by_ids(node_ids, self.nodes)
        nodes.extend(_nodes_by_ids(node_ids, self.annotations))
        return nodes

    def _update_groups(self) -> None:
        for group in self.groups:
            group.add_nodes(self._update_group_in_nodes)

    def _update_package_in_nodes(self, node_ids: Iterable[str]) -> List[CustomNode]:
        nodes = self.get_nodes(CustomNode)
        return [node for node in nodes if node.node_id in node_ids]

    def _update_packages(self) -> None:
        for dependency in self.get_dependencies(PackageDependency):
            dependency.add_nodes(self._update_package_in_nodes)

    def update_nodes(self) -> None:
        self._update_groups()
        self._update_packages()

    def has_dependencies(self, node_type: Type[TDependency]) -> bool:
        return len(self.get_dependencies(node_type)) > 0

    def get_dependencies(self, node_type: Type[TDependency]) -> List[TDependency]:
        nodes = [node for node in self.dependencies if isinstance(node, node_type)]
        return sorted(nodes, key=lambda dep: dep.name)

    def has_nodes(self, node_type: Type[TNode]) -> bool:
        return len(self.get_nodes(node_type)) > 0

    def get_nodes(self, node_type: Type[TNode]) -> List[TNode]:
        nodes = [node for node in self.nodes if isinstance(node, node_type)]
        return sorted(nodes, key=lambda node: (node.name, node.node_id))


@dataclass
class Script(ADynamoFileNode):
    inputs: List[InputOutputNode] = field(compare=False, repr=False)
    outputs: List[InputOutputNode] = field(compare=False, repr=False)

    def input_nodes(self) -> List[INode]:
        nodes = [node for node in self.nodes if node.is_input]
        for node in self.inputs:
            if node in nodes:
                continue
            nodes.append(node)
        return nodes

    def output_nodes(self) -> List[INode]:
        nodes = [node for node in self.nodes if node.is_output]
        for node in self.outputs:
            if node in nodes:
                continue
            nodes.append(node)
        return nodes


def default_package_info() -> 'PackageInfo':
    return PackageInfo(version='', license='', group='', keywords='', dependencies='',
                       contents='', engine_version='', site_url='', repository_url='')


def default_package() -> IPackage:
    return Package(name='', path=Path(), description='', info=default_package_info())


@dataclass
class CustomFileNode(ADynamoFileNode, ICustomNode):
    category: str = field(repr=True, compare=False)
    package: IPackage = field(default_factory=default_package, compare=False, repr=True)

    @property
    def full_name(self) -> str:
        return f'{self.name} [{self.package.full_name}]'


@dataclass
class PythonCustomFileNode(CustomFileNode):
    pass


@dataclass
class PackageInfo(IInfoModel):
    version: str = field(compare=True, repr=True)
    license: str = field(compare=False, repr=False)  # ""
    group: str = field(compare=False, repr=False)  # "RSRG"
    keywords: str = field(compare=False, repr=False)  # ["rsrg", "sersa", "rail"]
    dependencies: str = field(compare=False, repr=False)  # []
    contents: str = field(compare=False, repr=False)  # ""
    engine_version: str = field(compare=False, repr=False)  # "1.3.2.2480"
    # engine: str = field(compare=False, repr=False)  # "dynamo"
    # engine_metadata: str = field(compare=False, repr=False)  # ""
    site_url: str = field(compare=False, repr=False)  # "www.rhomberg-sersa.com/de"
    repository_url: str = field(compare=False, repr=False)  # ""
    # contains_binaries: str = field(compare=False, repr=False)  # false
    # node_libraries: str = field(compare=False, repr=False)  # [


@dataclass
class Package(AFileBaseModel, IPackage, IFileModel[CustomFileNode, PackageInfo]):
    name: str = field(hash=True, compare=True, repr=True)
    info: PackageInfo = field(compare=False, repr=False)
    nodes: List[CustomFileNode] = field(default_factory=list,
                                        compare=False, repr=False)

    @property
    def version(self) -> str:
        return self.info.version

    @property
    def full_name(self) -> str:
        return f'{self.name} [{self.version}]'

    def update_nodes(self) -> None:
        for node in self.nodes:
            node.update_nodes()
        model.add_to_nodes(self, self.nodes, ['package'])

    def by_category(self, category: str) -> List[CustomFileNode]:
        return [node for node in self.nodes if node.category == category]
