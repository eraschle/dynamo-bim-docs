from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, OrderedDict, Tuple, Type, TypeVar

from dynamo.models.files import (ADynamoFileNode, AFileBaseModel, Package,
                                 PythonCustomFileNode, Script)
from dynamo.models.nodes import DynamoNode
from dynamo.source.gateway import IBuilder, IFileBuilder, ISourceRepository
from dynamo.source.json.builder_nodes import (DependencyBuilder,
                                              DynamoNodeBuilder,
                                              annotation_node_builder,
                                              dynamo_info_builder,
                                              group_node_builder,
                                              input_node_builder,
                                              output_node_builder,
                                              package_info_builder)

TFileModel = TypeVar('TFileModel', bound=AFileBaseModel)
TBuilder = TypeVar('TBuilder', bound=IBuilder)


class AFileBuilder(ABC, IBuilder[TFileModel, ISourceRepository[Dict[str, Any]]]):

    @classmethod
    def attr_src_map(cls) -> Dict[str, Tuple[str, Any]]:
        """Dict with node attr as key and content attr as value"""
        raise NotImplementedError

    def __init__(self, node_type: Type[TFileModel]) -> None:
        super().__init__()
        self.node_type = node_type

    def get_attributes(self, repo: ISourceRepository[Dict[str, Any]]) -> Dict[str, Any]:
        attributes: Dict[str, Any] = {'path': repo.file_path}
        for attr, src_attr in self.attr_src_map().items():
            value = repo.content.get(*src_attr)
            attributes[attr] = self._get_value(attr, value)
        attributes.update(self.get_builder_attributes(repo))
        return attributes

    def _get_value(self, attr: str, value: Any) -> Any:
        return value

    def can_build(self, content: ISourceRepository[Dict[str, Any]], **kwargs) -> bool:
        return all(attr in content.content for (attr, _) in self.attr_src_map().values())

    @abstractmethod
    def get_builder_attributes(self, repo: ISourceRepository[Dict[str, Any]]) -> Dict[str, Any]:
        pass

    def build(self, content: ISourceRepository[Dict[str, Any]], **kwargs) -> TFileModel:
        attributes = self.get_attributes(content)
        return self.node_type(**attributes)


TDynamoFile = TypeVar('TDynamoFile', bound=ADynamoFileNode)


class ADynamoFileBuilder(AFileBuilder[TDynamoFile], IFileBuilder[TDynamoFile, ISourceRepository[Dict[str, Any]]]):

    node_cache: Dict[str, DynamoNode] = {}

    @classmethod
    def attr_src_map(cls) -> Dict[str, Tuple[str, Any]]:
        attr_map = {
            'uuid': ('Uuid', None),
            'name': ('Name', None),
            'description': ('Description', None)
        }
        return attr_map

    @classmethod
    def builder_map(cls) -> OrderedDict[str, Tuple[str, IBuilder]]:
        return {
            'info': ('dynamo_info', dynamo_info_builder()),
            'nodes': ('nodes', DynamoNodeBuilder()),
            'groups': ('groups', group_node_builder()),
            'dependencies': ('dependencies', DependencyBuilder()),
            'annotations': ('annotations', annotation_node_builder()),
        }  # type: ignore

    def _get_value(self, attr: str, value: Any) -> Any:
        if attr != 'description':
            return super()._get_value(attr, value)
        return '' if value is None else value

    def _build_nodes(self, repo: ISourceRepository[Dict[str, Any]], builder_info: Tuple[str, IBuilder], **kwargs) -> List[DynamoNode]:
        nodes = []
        func_name, builder = builder_info
        for node_content in getattr(repo, func_name)():
            if not builder.can_build(node_content, **kwargs):
                continue
            model = builder.build(node_content, **kwargs)
            if isinstance(model, DynamoNode):
                self.node_cache[model.node_id] = model
            nodes.append(model)
        return nodes

    def get_builder_attributes(self, repo: ISourceRepository[Dict[str, Any]]) -> Dict[str, Any]:
        attr_values = {}
        for attr, builder in self.builder_map().items():
            models = self._build_nodes(repo, builder)
            if attr == 'info':
                models = None if len(
                    models) == 0 else models[0]  # type: ignore
            attr_values[attr] = models
        return attr_values

    def _change_attr(self, node: TDynamoFile, content: ISourceRepository[Dict[str, Any]], attr_name: str, new_value: str) -> TDynamoFile:
        content.read(node.path)
        key, _ = self.attr_src_map()[attr_name]
        content.content[key] = new_value
        content.write(node.path, content.content)
        setattr(node, attr_name, new_value)
        return node

    def change_name(self, node: TDynamoFile, content: ISourceRepository[Dict[str, Any]], new_name: str) -> TDynamoFile:
        return self._change_attr(node, content, 'name', new_name)

    def change_uuid(self, node: TDynamoFile, repo: ISourceRepository[Dict[str, Any]], new_uuid: str) -> TDynamoFile:
        return self._change_attr(node, repo, 'uuid', new_uuid)


class ScriptFileBuilder(ADynamoFileBuilder[Script]):

    @classmethod
    def in_and_output_builder_map(cls) -> OrderedDict[str, Tuple[str, IBuilder]]:
        return {
            'inputs': ('inputs', input_node_builder()),
            'outputs': ('outputs', output_node_builder()),
        }  # type: ignore

    def __init__(self) -> None:
        super().__init__(Script)

    def _node_by_id(self, node_id: str) -> Optional[DynamoNode]:
        return self.node_cache.get(node_id)

    def _build_in_and_output_nodes(self, repo: ISourceRepository[Dict[str, Any]], builder_info: Tuple[str, IBuilder], **kwargs) -> List[DynamoNode]:
        nodes = []
        func_name, builder = builder_info
        for node_content in getattr(repo, func_name)():
            node_content['Node'] = self._node_by_id(node_content['Id'])
            if not builder.can_build(node_content, **kwargs):
                continue
            model = builder.build(node_content, **kwargs)
            nodes.append(model)
        return nodes

    def get_attributes(self, repo: ISourceRepository[Dict[str, Any]]) -> Dict[str, Any]:
        attr_values = super().get_attributes(repo)
        for attr, builder in self.in_and_output_builder_map().items():
            models = self._build_in_and_output_nodes(repo, builder)
            attr_values[attr] = models
        return attr_values


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

    def _build_nodes(self, repo: ISourceRepository[Dict[str, Any]], builder_info: Tuple[str, IBuilder], **kwargs) -> DynamoNode:
        func_name, builder = builder_info
        node_content = getattr(repo, func_name)()
        if not builder.can_build(node_content, **kwargs):
            raise ValueError(f'Content of {func_name} can not be created')
        return builder.build(node_content, **kwargs)

    def get_builder_attributes(self, repo: ISourceRepository[Dict[str, Any]]) -> Dict[str, Any]:
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
