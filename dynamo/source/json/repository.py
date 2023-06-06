from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from dynamo.io.file import JsonHandler
from dynamo.source.gateway import ISourceRepository


class JsonFileRepository(ISourceRepository[Dict[str, Any]]):

    def __init__(self, file_handler: JsonHandler) -> None:
        super().__init__()
        self.file_handler = file_handler
        self.file_path: Path = Path()

    def can_read(self, path: Path):
        self.file_handler.extension = path.suffix
        return self.file_handler.can_read(path)

    def read(self, path: Path):
        self.file_handler.extension = path.suffix
        self.content = self.file_handler.read(path)
        self.file_path = path

    def write(self, path: Path, content: Dict[str, Any]):
        self.file_handler.write(path, content)

    def get_value(self, key: str, default: Any) -> Any:
        return self.content.get(key, default)

    def _node_id(self, content: Dict[str, Any]) -> str:
        return content.get('Id', '')

    def _get_content(self, keys: Iterable[str]) -> List[Dict[str, Any]]:
        content = self.content
        for key in keys:
            content = content.get(key, {})
        return content if isinstance(content, List) else [content]

    def nodes(self) -> List[Dict[str, Any]]:
        nodes = []
        for node in self._get_content(['Nodes']):
            node_view = self.node_view_by(self._node_id(node))
            node.update(node_view)
            nodes.append(node)
        return nodes

    def node_views(self) -> List[Dict[str, Any]]:
        return self._get_content(['View', 'NodeViews'])

    def node_view_by(self, node_id) -> Dict[str, Any]:
        for view in self.node_views():
            if self._node_id(view) != node_id:
                continue
            return view
        return {}

    def _by_callbacks(self, node_contents: List[Dict[str, Any]], cb_filters: Dict[str, Callable[[Any], bool]]) -> List[Dict[str, Any]]:
        filtered = []
        for content in node_contents:
            if not all(cb(content.get(attr)) for attr, cb in cb_filters.items()):
                continue
            filtered.append(content)
        return filtered

    def inputs(self) -> List[Dict[str, Any]]:
        return self._get_content(['Inputs'])

    def outputs(self) -> List[Dict[str, Any]]:
        return self._get_content(['Outputs'])

    def _get_annotations(self) -> List[Dict[str, Any]]:
        return self._get_content(['View', 'Annotations'])

    def groups(self) -> List[Dict[str, Any]]:
        def is_group(value: Any) -> bool:
            return isinstance(value, List) and len(value) > 0

        return self._by_callbacks(
            self._get_annotations(), {'Nodes': is_group}
        )

    def annotations(self) -> List[Dict[str, Any]]:
        def is_annotation(value: Any) -> bool:
            return isinstance(value, List) and len(value) == 0

        return self._by_callbacks(
            self._get_annotations(), {'Nodes': is_annotation}
        )

    def _get_dependencies(self) -> List[Dict[str, Any]]:
        return self._get_content(['NodeLibraryDependencies'])

    def _package_dependencies(self) -> List[Dict[str, Any]]:
        def is_package(value: Any) -> bool:
            return isinstance(value, str) and value == 'Package'

        return self._by_callbacks(
            self._get_dependencies(), {'ReferenceType': is_package}
        )

    def _external_dependencies(self) -> List[Dict[str, Any]]:
        def is_external(value: Any) -> bool:
            return isinstance(value, str) and value == 'External'

        return self._by_callbacks(
            self._get_dependencies(), {'ReferenceType': is_external}
        )

    def dependencies(self) -> List[Dict[str, Any]]:
        dependencies = []
        dependencies.extend(self._package_dependencies())
        dependencies.extend(self._external_dependencies())
        return dependencies

    def _common_info(self, keys: Iterable[str]) -> Dict[str, Any]:
        nodes = self._get_content(keys)
        first = nodes[0]
        if isinstance(first, Dict):
            return first
        raise ValueError(f'Excepted Dict but got {type(first)}')

    def dynamo_info(self) -> Dict[str, Any]:
        info = self._get_content(['View', 'Dynamo'])
        return {} if len(info) < 1 else info[0]

    def package_info(self) -> Dict[str, Any]:
        return self._common_info([])
