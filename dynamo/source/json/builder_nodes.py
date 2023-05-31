from typing import Any, Dict, Iterable, Optional, Tuple, Type, TypeVar

from dynamo.models.files import DynamoInfo, PackageInfo
from dynamo.models.model import IDependency
from dynamo.models.nodes import (ABaseModel, Annotation, CodeBlockNode,
                                 CustomNetNode, CustomPythonNode, DirInputNode,
                                 DynamoNode, ExternalDependency, FileInputNode, GeneralNode,
                                 Group, PackageDependency, PythonCodeNode)
from dynamo.source.gateway import IBuilder

TModel = TypeVar('TModel', bound=ABaseModel | Annotation | DynamoInfo | PackageInfo)


class NodeBuilder(IBuilder[TModel, Dict[str, Any]]):

    def __init__(self, node_type: Type[TModel], attr_map: Dict[str, Tuple[str, Any]],
                 build_values: Optional[Dict[str, str]] = None) -> None:
        super().__init__()
        self.node_type = node_type
        self.attr_map = attr_map
        self.build_values = build_values or {}

    def _keys_exists(self, content: Dict[str, Any]) -> bool:
        return all(content.get(key) is not None for key in self.build_values)

    def _build_values_exists(self, content: Dict[str, Any], **kwargs) -> bool:
        for src_attr, src_value in self.build_values.items():
            if content.get(src_attr, None) == src_value:
                continue
            return False
        return True

    def can_build(self, content: Dict[str, Any], **kwargs) -> bool:
        return (len(content) > 0
                and self._keys_exists(content)
                and self._build_values_exists(content, **kwargs))

    def get_attributes(self, content: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        attr_values = {}
        for attr, src_attr in self.attr_map.items():
            attr_values[attr] = content.get(*src_attr)
        return attr_values

    def build(self, content: Dict[str, Any], **kwargs) -> TModel:
        attributes = self.get_attributes(content, **kwargs)
        return self.node_type(**attributes)


class GeneralNodeBuilder(NodeBuilder[GeneralNode]):

    def __init__(self, attr_map: Dict[str, Tuple[str, Any]]) -> None:
        super().__init__(GeneralNode, attr_map, {})

    def can_build(self, content: Dict[str, Any], **kwargs) -> bool:
        return len(content) > 0 and True


def _node_attr_src_map() -> Dict[str, Tuple[str, Any]]:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'node_id': ('Id', None),
        'description': ('Description', None),
        # 'replication': ('Disabled', None),
        'name': ('Name', None),
        'disabled': ('Excluded', None),
        'show_geometry': ('ShowGeometry', None),
        'x': ('X', None),
        'y': ('Y', None)
    }
    return attr_map


def custom_python_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'uuid': ('FunctionSignature', None)
    }
    attr_map.update(_node_attr_src_map())
    build_values = {
        "ConcreteType": "Dynamo.Graph.Nodes.CustomNodes.Function, DynamoCore",
        "NodeType": "FunctionNode",
    }
    return NodeBuilder(CustomPythonNode, attr_map, build_values)


def custom_net_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'uuid': ('FunctionSignature', None)
    }
    attr_map.update(_node_attr_src_map())
    build_values = {
        "ConcreteType": "Dynamo.Graph.Nodes.ZeroTouch.DSFunction, DynamoCore",
        "NodeType": "FunctionNode",
    }
    return NodeBuilder(CustomNetNode, attr_map, build_values)


def _code_node_attr_src_map() -> Dict[str, Tuple[str, Any]]:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'code': ('Code', None)
    }
    attr_map.update(_node_attr_src_map())
    return attr_map


def code_block_builder() -> NodeBuilder:
    attr_map = _code_node_attr_src_map()
    build_values = {
        "ConcreteType": "Dynamo.Graph.Nodes.CodeBlockNodeModel, DynamoCore",
        "NodeType": "CodeBlockNode",
    }
    return NodeBuilder(CodeBlockNode, attr_map, build_values)


def python_node_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'engine': ('Engine', 'Iron-Python 2')
    }
    attr_map.update(_code_node_attr_src_map())
    build_values = {
        "ConcreteType": "PythonNodeModels.PythonNode, PythonNodeModels",
        "NodeType": "PythonScriptNode",
    }
    return NodeBuilder(PythonCodeNode, attr_map, build_values)


def _path_node_builder() -> Dict[str, Tuple[str, Any]]:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'hint_path': ('HintPath', None),
        'input_value': ('InputValue', None)
    }
    attr_map.update(_node_attr_src_map())
    return attr_map


def file_node_builder() -> NodeBuilder:
    attr_map = _path_node_builder()
    build_values = {
        "ConcreteType": "CoreNodeModels.Input.Filename, CoreNodeModels",
        "NodeType": "ExtensionNode",
    }
    return NodeBuilder(FileInputNode, attr_map, build_values)


def dir_node_builder() -> NodeBuilder:
    attr_map = _path_node_builder()
    build_values = {
        "ConcreteType": "CoreNodeModels.Input.Directory, CoreNodeModels",
        "NodeType": "ExtensionNode",
    }
    return NodeBuilder(DirInputNode, attr_map, build_values)


def general_node_builder() -> NodeBuilder:
    attr_map = _node_attr_src_map()
    return GeneralNodeBuilder(attr_map)


def node_builders() -> Iterable[NodeBuilder]:
    return [
        custom_python_builder(),
        custom_net_builder(),
        code_block_builder(),
        python_node_builder(),
        file_node_builder(),
        dir_node_builder(),
        general_node_builder(),
    ]


class DynamoNodeBuilder(IBuilder[DynamoNode, Dict[str, Any]]):

    def __init__(self, builders: Optional[Iterable[NodeBuilder]] = None) -> None:
        super().__init__()
        self.builders = builders or node_builders()

    def _build_by(self, content: Dict[str, Any], **kwargs) -> Optional[NodeBuilder]:
        for builder in self.builders:
            if not builder.can_build(content, **kwargs):
                continue
            return builder
        return None

    def can_build(self, content: Dict[str, Any], **kwargs) -> bool:
        return self._build_by(content, **kwargs) is not None

    def build(self, content: Dict[str, Any], **kwargs) -> Optional[DynamoNode]:
        builder = self._build_by(content, **kwargs)
        return None if builder is None else builder.build(content, **kwargs)


def _package_dependency_builder() -> NodeBuilder:
    attr_map = {
        'name': ('Name', None),
        'version': ('Version', None),
        'node_ids': ('Nodes', []),
    }
    return NodeBuilder(PackageDependency, attr_map)


def _external_dependency_builder() -> NodeBuilder:
    attr_map = {
        'name': ('Name', None),
        'node_ids': ('Nodes', []),
    }
    return NodeBuilder(ExternalDependency, attr_map)


def dependency_builders() -> Iterable[NodeBuilder]:
    return [
        _package_dependency_builder(),
        _external_dependency_builder(),
    ]


class DependencyBuilder(IBuilder[IDependency, Dict[str, Any]]):

    def __init__(self, builders: Optional[Iterable[NodeBuilder]] = None) -> None:
        super().__init__()
        self.builders = builders or dependency_builders()

    def _build_by(self, content: Dict[str, Any], **kwargs) -> Optional[NodeBuilder]:
        for builder in self.builders:
            if not builder.can_build(content, **kwargs):
                continue
            return builder
        return None

    def can_build(self, content: Dict[str, Any], **kwargs) -> bool:
        return self._build_by(content, **kwargs) is not None

    def build(self, content: Dict[str, Any], **kwargs) -> Optional[DynamoNode]:
        builder = self._build_by(content, **kwargs)
        return None if builder is None else builder.build(content, **kwargs)


class AnnotationBuilder(NodeBuilder[Annotation]):

    def __init__(self, attr_map: Dict[str, Tuple[str, Any]]) -> None:
        super().__init__(Annotation, attr_map, {})

    def can_build(self, content: Dict[str, Any], **kwargs) -> bool:
        return len(content.get('Nodes', [])) == 0


def annotation_node_builder() -> NodeBuilder:
    attr_map = {
        'node_id': ('Id', None),
        'description': ('Title', None),
        'x': ('Left', None),
        'y': ('Top', None),
    }
    return AnnotationBuilder(attr_map)


class GroupBuilder(NodeBuilder[Group]):

    def __init__(self, attr_map: Dict[str, Tuple[str, Any]]) -> None:
        super().__init__(Group, attr_map, {})

    def can_build(self, content: Dict[str, Any], **kwargs) -> bool:
        return len(content.get('Nodes', [])) > 0


def group_node_builder() -> NodeBuilder:
    attr_map = {
        'node_id': ('Id', None),
        'name': ('Title', None),
        'description': ('DescriptionText', None),
        'node_ids': ('Nodes', []),
        'color': ('Background', None),
        'x': ('Left', None),
        'y': ('Top', None),
    }
    return GroupBuilder(attr_map)


def dynamo_info_builder() -> NodeBuilder:
    attr_map = {
        'scale_factor': ('ScaleFactor', DynamoNode),
        'has_run_without_crash': ('HasRunWithoutCrash', DynamoNode),
        'is_visible_in_library': ('IsVisibleInDynamoLibrary', DynamoNode),
        'version': ('Version', DynamoNode),
        'run_type': ('Manual', DynamoNode),
    }
    return NodeBuilder(DynamoInfo, attr_map)


def package_info_builder() -> NodeBuilder:
    attr_map = {
        'version': ('version', DynamoNode),
        'license': ('license', DynamoNode),
        'group': ('group', DynamoNode),
        'keywords': ('keywords', DynamoNode),
        'dependencies': ('dependencies', DynamoNode),
        'contents': ('contents', DynamoNode),
        'engine_version': ('engine_version', DynamoNode),
        'site_url': ('site_url', DynamoNode),
        'repository_url': ('repository_url', DynamoNode),
    }
    return NodeBuilder(PackageInfo, attr_map)


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
