from typing import (Any, Callable, Dict, Iterable, Optional, Tuple, Type,
                    TypeVar)

from dynamo.models.files import DynamoInfo, PackageInfo
from dynamo.models.model import IDependency
from dynamo.models.nodes import (ABaseModel, Annotation, CodeBlockNode,
                                 CustomNetNode, CustomPythonNode, DirPathNode,
                                 DynamoNode, ExternalDependency, FilePathNode,
                                 GeneralNode, Group, InputCoreNode,
                                 InputOutputNode, PackageDependency,
                                 PythonCodeNode, SelectionNode)
from dynamo.source.gateway import IBuilder, TModel
from dynamo.utils import checks


class ABuilder(IBuilder[TModel, Dict[str, Any]]):

    def __init__(self, node_type: Type[TModel], attr_map: Dict[str, Tuple[str, Any]],
                 build_values: Optional[Dict[str, str | Callable[[Optional[str]], bool]]] = None) -> None:
        super().__init__()
        self.node_type = node_type
        self.attr_map = attr_map
        self.build_values = build_values or {}

    def _keys_exists(self, content: Dict[str, Any]) -> bool:
        return all(content.get(key) is not None for key in self.build_values)

    def can_build(self, content: Dict[str, Any], **kwargs) -> bool:
        return len(content) > 0 and self._keys_exists(content)

    def get_attributes(self, content: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        attr_values = {}
        for attr, src_attr in self.attr_map.items():
            attr_values[attr] = content.get(*src_attr)
        return attr_values

    def build(self, content: Dict[str, Any], **kwargs) -> TModel:
        attributes = self.get_attributes(content, **kwargs)
        return self.node_type(**attributes)


TNode = TypeVar(
    'TNode', bound=ABaseModel | Annotation | DynamoInfo | PackageInfo
)


class NodeBuilder(ABuilder[TNode]):

    def _build_values_exists(self, content: Dict[str, Any], **kwargs) -> bool:
        for src_attr, src_value in self.build_values.items():
            value = content.get(src_attr, None)
            if isinstance(src_value, str) and value == src_value:
                continue
            if not isinstance(src_value, str) and src_value(value):
                continue
            return False
        return True

    def can_build(self, content: Dict[str, Any], **kwargs) -> bool:
        if not super().can_build(content, **kwargs):
            return False
        return self._build_values_exists(content, **kwargs)


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
        'is_input': ('IsSetAsInput', False),
        'is_output': ('IsSetAsOutput', False),
        'x': ('X', None),
        'y': ('Y', None)
    }
    return attr_map


def custom_python_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'uuid': ('FunctionSignature', None)
    }
    attr_map.update(_node_attr_src_map())

    build_values: Dict[str, str | Callable[[Optional[str]], bool]] = {
        "ConcreteType": "Dynamo.Graph.Nodes.CustomNodes.Function, DynamoCore",
        "NodeType": "FunctionNode",
    }
    return NodeBuilder(CustomPythonNode, attr_map, build_values)


def custom_net_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'uuid': ('FunctionSignature', None)
    }
    attr_map.update(_node_attr_src_map())

    build_values: Dict[str, str | Callable[[Optional[str]], bool]] = {
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

    build_values: Dict[str, str | Callable[[Optional[str]], bool]] = {
        "ConcreteType": "Dynamo.Graph.Nodes.CodeBlockNodeModel, DynamoCore",
        "NodeType": "CodeBlockNode",
    }
    return NodeBuilder(CodeBlockNode, attr_map, build_values)


def python_node_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'engine': ('Engine', 'Iron-Python 2')
    }
    attr_map.update(_code_node_attr_src_map())

    build_values: Dict[str, str | Callable[[Optional[str]], bool]] = {
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

    build_values: Dict[str, str | Callable[[Optional[str]], bool]] = {
        "ConcreteType": "CoreNodeModels.Input.Filename, CoreNodeModels",
        "NodeType": "ExtensionNode",
    }
    return NodeBuilder(FilePathNode, attr_map, build_values)


def dir_node_builder() -> NodeBuilder:
    attr_map = _path_node_builder()

    build_values: Dict[str, str | Callable[[Optional[str]], bool]] = {
        "ConcreteType": "CoreNodeModels.Input.Directory, CoreNodeModels",
        "NodeType": "ExtensionNode",
    }
    return NodeBuilder(DirPathNode, attr_map, build_values)


def __is_input_core(value: Optional[str]) -> bool:
    if not checks.is_not_blank(value):
        return False
    return value.endswith('InputNode')


def core_input_node_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'value': ('InputValue', None),
    }
    attr_map.update(_node_attr_src_map())

    build_values: Dict[str, str | Callable[[Optional[str]], bool]] = {
        "NodeType": __is_input_core,
        "InputValue": checks.is_not_blank,
    }
    return NodeBuilder(InputCoreNode, attr_map, build_values)


def selection_node_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'selected': ('SelectedString', None),
    }
    attr_map.update(_node_attr_src_map())

    build_values: Dict[str, str | Callable[[Optional[str]], bool]] = {
        "NodeType": "ExtensionNode",
        "SelectedString": checks.is_not_blank,
    }
    return NodeBuilder(SelectionNode, attr_map, build_values)


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
        selection_node_builder(),
        core_input_node_builder(),
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


class InputOutputNodeBuilder(ABuilder[InputOutputNode]):
    def __init__(self, attr_map: Dict[str, Tuple[str, Any]]) -> None:
        super().__init__(InputOutputNode, attr_map, None)

    def can_build(self, content: Dict[str, Any], **_) -> bool:
        return content.get(*self.attr_map['node']) is not None


def _input_output_node_attr() -> Dict[str, Tuple[str, Any]]:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'node': ('Node', None),
        'value_type': ('Type', None)
    }
    return attr_map


def input_node_builder() -> IBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'value': ('Value', None)
    }
    attr_map.update(_input_output_node_attr())
    return InputOutputNodeBuilder(attr_map)


def output_node_builder() -> IBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'value': ('InitialValue', None)
    }
    attr_map.update(_input_output_node_attr())
    return InputOutputNodeBuilder(attr_map)


def _package_dependency_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'name': ('Name', None),
        'version': ('Version', None),
        'node_ids': ('Nodes', []),
    }
    return NodeBuilder(PackageDependency, attr_map)


def _external_dependency_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
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
    attr_map: Dict[str, Tuple[str, Any]] = {
        'node_id': ('Id', None),
        'name': ('Title', None),
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
    attr_map: Dict[str, Tuple[str, Any]] = {
        'node_id': ('Id', None),
        'name': ('Title', None),
        'description': ('DescriptionText', ''),
        'node_ids': ('Nodes', []),
        'color': ('Background', None),
        'x': ('Left', None),
        'y': ('Top', None),
    }
    return GroupBuilder(attr_map)


def dynamo_info_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
        'scale_factor': ('ScaleFactor', DynamoNode),
        'has_run_without_crash': ('HasRunWithoutCrash', DynamoNode),
        'is_visible_in_library': ('IsVisibleInDynamoLibrary', DynamoNode),
        'version': ('Version', DynamoNode),
        'run_type': ('Manual', DynamoNode),
    }
    return NodeBuilder(DynamoInfo, attr_map)


def package_info_builder() -> NodeBuilder:
    attr_map: Dict[str, Tuple[str, Any]] = {
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
