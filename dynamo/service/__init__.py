
from typing import Iterable

from dynamo.io.file import JsonHandler
from dynamo.models.files import Package, Script
from dynamo.service.protocol import IDynamoManager
from dynamo.source.gateway import INodeGateway
from dynamo.source.json.builder_files import (CustomNodeFileBuilder,
                                              PackageFileBuilder,
                                              ScriptFileBuilder)
from dynamo.source.json.factory import JsonDynamoFactory
from dynamo.source.json.gateway import JsonDynamoGateway
from dynamo.source.json.repository import JsonFileRepository


def json_gateway(manager: IDynamoManager) -> INodeGateway:
    factory = JsonDynamoFactory(ScriptFileBuilder(),
                                CustomNodeFileBuilder(),
                                PackageFileBuilder(),
                                JsonFileRepository(JsonHandler()))
    return JsonDynamoGateway(factory, manager)


def get_packages(manager: IDynamoManager) -> Iterable[Package]:
    gateway = json_gateway(manager)
    return gateway.packages([manager.package_src_path])


def get_scripts(manager: IDynamoManager) -> Iterable[Script]:
    gateway = json_gateway(manager)
    return gateway.scripts([manager.script_src_path])
