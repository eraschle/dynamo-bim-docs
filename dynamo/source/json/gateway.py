from pathlib import Path
from typing import Any, Dict, Iterable, List

from dynamo.models.files import (CustomFileNode, IDynamoFile, Package,
                                 PythonCustomFileNode, Script)
from dynamo.source.gateway import (IDynamoFactory, IFileBuilder, INodeGateway,
                                   INodeRepository, TDynamoFile)
from dynamo.utils.crawler import (ExtensionCrawleOption,
                                  RemoveExtensionCrawleOption, async_crawling)


class JsonDynamoGateway(INodeGateway):
    def __init__(self, factory: IDynamoFactory[Dict[str, Any]], repository: INodeRepository) -> None:
        super().__init__()
        self.scripts: List[Script] = []
        self.packages: List[Package] = []
        self.factory = factory
        self.repository = repository

    def _get_builder(self, node: IDynamoFile) -> IFileBuilder:
        if isinstance(node, Script):
            return self.factory.script_builder
        if isinstance(node, PythonCustomFileNode):
            return self.factory.custom_node_builder
        raise ValueError(f'Node must be a {Script} or {CustomFileNode}')

    def change_name(self, node: TDynamoFile, new_name: str) -> TDynamoFile:
        builder = self._get_builder(node)
        builder.change_name(node, self.factory.repository, new_name)
        return node

    def change_uuid(self, node: TDynamoFile, new_uuid: str) -> TDynamoFile:
        builder = self._get_builder(node)
        builder.change_uuid(node, self.factory.repository, new_uuid)
        return node

    def _get_options(self, extension: str) -> ExtensionCrawleOption:
        return ExtensionCrawleOption([extension])

    def read_scripts(self, paths: Iterable[Path]) -> List[Script]:
        for path in async_crawling(paths, self._get_options('dyn')):
            if not self.factory.can_create(path):
                print(f'SCRIPT not created "{path}"')
                continue
            script = self.factory.script(path)
            self.scripts.append(script)
        return self.scripts

    def custom_nodes(self, path: Path) -> List[CustomFileNode]:
        nodes = []
        for node_path in async_crawling([path], self._get_options('dyf')):
            try:
                if not self.factory.can_create(node_path):
                    print(f'CUSTOM NODE not created "{node_path}"')
                    continue
                node = self.factory.custom_node(node_path)
                nodes.append(node)
            except UnicodeEncodeError as err:
                print(f'Custom Node: Encode Error {str(path.absolute())} [{str(err)}]')
        return nodes

    def _unique_packages(self, paths: Iterable[Path]) -> Iterable[Package]:
        packages = {}
        for path in async_crawling(paths, self._get_options('json')):
            try:
                if not self.factory.can_create(path):
                    print(f'PACKAGE not created "{path}"')
                    continue
                package = self.factory.package(path)
                packages[package.full_name] = package
            except UnicodeEncodeError as err:
                print(f'Package: Encode Error {str(path.absolute())} [{str(err)}]')
        return sorted(packages.values(), key=lambda pkg: pkg.full_name)

    def read_packages(self, paths: Iterable[Path]) -> List[Package]:
        for package in self._unique_packages(paths):
            package.nodes.extend(self.custom_nodes(package.path.parent))
            package.update_nodes()
            self.repository.add(package)
            self.packages.append(package)
        return self.packages

    def documentations(self, paths: Iterable[Path]) -> List[Path]:
        paths = [path for path in paths if path.exists()]
        return async_crawling(paths, self._get_options('org'))

    def html_documentations(self, paths: Iterable[Path]) -> List[Path]:
        paths = [path for path in paths if path.exists()]
        return async_crawling(paths, RemoveExtensionCrawleOption(['html']))
