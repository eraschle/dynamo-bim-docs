from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, OrderedDict, Tuple, Type, TypeVar

from dynamo.models.files import (ADynamoFileNode, AFileBaseModel, Package,
                                 PythonCustomFileNode, Script)
from dynamo.models.nodes import ANode
from dynamo.source.gateway import IBuilder, ISourceRepository
from dynamo.source.json.builder_nodes import (DependencyBuilder, DynamoNodeBuilder, NodeBuilder,
                                              annotation_node_builder,
                                              dynamo_info_builder,
                                              group_node_builder,
                                              package_info_builder)

TFileModel = TypeVar('TFileModel', bound=AFileBaseModel)
TBuilder = TypeVar('TBuilder', bound=NodeBuilder)


class AFileBuilder(ABC, IBuilder[TFileModel, ISourceRepository]):

    @classmethod
    def attr_src_map(cls) -> Dict[str, Tuple[str, Any]]:
        """Dict with node attr as key and content attr as value"""
        raise NotImplementedError

    def __init__(self, node_type: Type[TFileModel]) -> None:
        super().__init__()
        self.node_type = node_type

    def get_attributes(self, repo: ISourceRepository) -> Dict[str, Any]:
        attributes = {'path': repo.file_path}
        for attr, src_attr in self.attr_src_map().items():
            attributes[attr] = repo.content.get(*src_attr)
        attributes.update(self.get_builder_attributes(repo))
        return attributes

    def can_build(self, repo: ISourceRepository) -> bool:
        return all(attr in repo.content for (attr, _) in self.attr_src_map().values())

    @abstractmethod
    def get_builder_attributes(self, repo: ISourceRepository) -> Dict[str, Any]:
        pass

    def build(self, repo: ISourceRepository) -> TFileModel:
        attributes = self.get_attributes(repo)
        return self.node_type(**attributes)


TDynamoFile = TypeVar('TDynamoFile', bound=ADynamoFileNode)


class ADynamoFileBuilder(AFileBuilder[TDynamoFile]):

    node_cache: Dict[str, ANode] = {}

    @classmethod
    def attr_src_map(cls) -> Dict[str, Tuple[str, Any]]:
        attr_map = {
            'uuid': ('Uuid', None),
            'name': ('Name', None),
            'description': ('Description', None),
        }
        return attr_map

    @classmethod
    def builder_map(cls) -> OrderedDict[str, Tuple[str, NodeBuilder]]:
        return {
            'info': ('dynamo_info', dynamo_info_builder()),
            'nodes': ('nodes', DynamoNodeBuilder()),
            'groups': ('groups', group_node_builder()),
            'dependencies': ('dependencies', DependencyBuilder()),
            'annotations': ('annotations', annotation_node_builder()),
        }  # type: ignore

    def _get_nodes(self, node_ids: Iterable[str]) -> List[ANode]:
        nodes = [self.node_cache.get(node_id, None) for node_id in node_ids]
        return [node for node in nodes if node is not None]

    def _build_nodes(self, repo: ISourceRepository, builder_info: Tuple[str, NodeBuilder], **kwargs) -> List[ANode]:
        nodes = []
        func_name, builder = builder_info
        for node_content in getattr(repo, func_name)():
            if not builder.can_build(node_content, **kwargs):
                continue
            model = builder.build(node_content, **kwargs)
            if isinstance(model, ANode):
                self.node_cache[model.node_id] = model
            nodes.append(model)
        return nodes

    def get_builder_attributes(self, repo: ISourceRepository) -> Dict[str, Any]:
        attr_values = {}
        for attr, builder in self.builder_map().items():
            models = self._build_nodes(repo, builder)
            if attr == 'info':
                models = None if len(models) == 0 else models[0]
            attr_values[attr] = models
        return attr_values


class ScriptFileBuilder(ADynamoFileBuilder[Script]):

    def __init__(self) -> None:
        super().__init__(Script)


class CustomNodeFileBuilder(ADynamoFileBuilder[PythonCustomFileNode]):

    @classmethod
    def attr_src_map(cls) -> Dict[str, Tuple[str, Any]]:
        attr_map: Dict[str, Tuple[str, Any]] = {
            'category': ('Category', None)
        }
        attr_map.update(super().attr_src_map())
        return attr_map

    def __init__(self) -> None:
        super().__init__(PythonCustomFileNode)


class PackageFileBuilder(AFileBuilder[Package]):

    @classmethod
    def attr_src_map(cls) -> Dict[str, Tuple[str, Any]]:
        attr_map = {
            'name': ('name', None),
            'description': ('description', None),
        }
        return attr_map

    @classmethod
    def builder_map(cls) -> OrderedDict[str, Tuple[str, IBuilder]]:
        return {
            'info': ('package_info', package_info_builder()),
            # 'nodes': ('common_info', package_info_builder()),
        }  # type: ignore

    def __init__(self) -> None:
        super().__init__(Package)

    def _build_nodes(self, repo: ISourceRepository, builder_info: Tuple[str, IBuilder], **kwargs) -> ANode:
        func_name, builder = builder_info
        node_content = getattr(repo, func_name)()
        if not builder.can_build(node_content, **kwargs):
            raise ValueError(f'Content of {func_name} can not be created')
        return builder.build(node_content, **kwargs)

    def get_builder_attributes(self, repo: ISourceRepository) -> Dict[str, Any]:
        attr_values = {}
        for attr, builder in self.builder_map().items():
            model = self._build_nodes(repo, builder)
            attr_values[attr] = model
        return attr_values


# _ACAD_NAMES = [name.lower() for name in ('Revit', 'Civil', 'Autodesk', 'ACAD')]


# class AutodeskNodeBuilder(ANodeBuilder):

#     def _is_autodesk_node(self, namespace: str) -> bool:
#         namespace = namespace.lower().strip()
#         return any(app_name in namespace for app_name in _ACAD_NAMES)

#     def is_node(self, source: SourceDynamoNode) -> bool:
#         namespaces = source.ConcreteType.split(',')
#         return any(self._is_autodesk_node(name) for name in namespaces)

#     def create_node(self, source: SourceDynamoNode) -> DynamoBase:
#         return self._create_node(source, AutodeskDynamoNode)
