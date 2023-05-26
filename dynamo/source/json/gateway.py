from pathlib import Path
from typing import Iterable, List

from dynamo.models.files import CustomFileNode, Package, Script
from dynamo.source.gateway import IDynamoFactory, INodeGateway, INodeRepository
from dynamo.utils.crawler import (ExtensionCrawleOption,
                                  RemoveExtensionCrawleOption, async_crawling)


class JsonDynamoGateway(INodeGateway):
    def __init__(self, factory: IDynamoFactory, repository: INodeRepository) -> None:
        super().__init__()
        self.factory = factory
        self.repository = repository

    def _get_options(self, extension: str) -> ExtensionCrawleOption:
        return ExtensionCrawleOption([extension])

    def scripts(self, paths: Iterable[Path]) -> List[Script]:
        scripts = []
        for path in async_crawling(paths, self._get_options('dyn')):
            if not self.factory.can_create(path):
                print(f'SCRIPT not created "{path}"')
                continue
            script = self.factory.script(path)
            scripts.append(script)
        return scripts

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

    def packages(self, paths: Iterable[Path]) -> List[Package]:
        packages = []
        for package in self._unique_packages(paths):
            package.nodes.extend(self.custom_nodes(package.path.parent))
            package.update_nodes()
            self.repository.add(package)
            packages.append(package)
        return packages

    def documentations(self, paths: Iterable[Path]) -> List[Path]:
        paths = [path for path in paths if path.exists()]
        return async_crawling(paths, self._get_options('org'))

    def html_documentations(self, paths: Iterable[Path]) -> List[Path]:
        paths = [path for path in paths if path.exists()]
        return async_crawling(paths, RemoveExtensionCrawleOption(['html']))
