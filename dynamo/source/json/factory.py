from pathlib import Path

from dynamo.models.files import CustomFileNode, Package, Script
from dynamo.source.gateway import IDynamoFactory
from dynamo.source.json.builder_files import (CustomNodeFileBuilder,
                                              PackageFileBuilder,
                                              ScriptFileBuilder)
from dynamo.source.json.repository import JsonFileRepository


class JsonDynamoFactory(IDynamoFactory):
    def __init__(self, script: ScriptFileBuilder, custom_node: CustomNodeFileBuilder,
                 package: PackageFileBuilder, repository: JsonFileRepository) -> None:
        self.script_builder = script
        self.custom_node_builder = custom_node
        self.package_builder = package
        self.repository = repository

    def can_create(self, path: Path) -> bool:
        try:
            return self.repository.can_read(path)
        except FileNotFoundError:
            return True

    def script(self, path: Path) -> Script:
        self.repository.read(path)
        if not self.script_builder.can_build(self.repository):
            raise ValueError(f'Script [{path.name}] can not be created')
        script = self.script_builder.build(self.repository)
        script.update_nodes()
        return script

    def package(self, path: Path) -> Package:
        self.repository.read(path)
        if not self.package_builder.can_build(self.repository):
            raise ValueError(f'Package [{path.name}] can not be created')
        return self.package_builder.build(self.repository)

    def custom_node(self, path: Path) -> CustomFileNode:
        self.repository.read(path)
        if not self.custom_node_builder.can_build(self.repository):
            raise ValueError(f'Python Custom node [{path.name}] can not be created')
        custom_node = self.custom_node_builder.build(self.repository)
        custom_node.update_nodes()
        return custom_node
