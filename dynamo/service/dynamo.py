import os
from pathlib import Path
from typing import Dict, Optional

from dynamo.models.files import CustomFileNode, Package
from dynamo.models.nodes import CustomNode, ICustomNode
from dynamo.service.protocol import IDynamoManager

WINDOWS = Path(
    'C:/workspace/projects/weichenlos/Bestandsmodellierung/00_Projektübergreifend/Skripte und Vorlagen')
WSL = Path('/home/elyo/workspace/__data__')


def _to_os(path: str) -> Path:
    if os.name == 'nt':
        return WINDOWS / path
    return WSL / path.lower()


DYNAMO_ROOT = Path(
    _to_os('Dynamo')
)


DOC_ROOT = Path(
    _to_os('Dynamo/docs/org/')
)


class DynamoManager(IDynamoManager):

    @classmethod
    def script_folder(cls) -> str:
        return 'Skripte'

    @classmethod
    def package_folder(cls) -> str:
        return 'Packages'

    def __init__(self, src_path: Path) -> None:
        super().__init__()
        self.src_path = src_path
        self.uuid_dict: Dict[str, CustomFileNode] = {}

    def _uuid_key(self, node: ICustomNode) -> str:
        return f'{node.uuid}-{node.package.version}'

    def add(self, package: Package):
        for node in package.nodes:
            node_key = self._uuid_key(node)
            self.uuid_dict[node_key] = node

    def get(self, node: CustomNode) -> Optional[CustomFileNode]:
        node_key = self._uuid_key(node)
        return self.uuid_dict.get(node_key, None)

    @property
    def script_src_path(self) -> Path:
        return self.src_path / self.script_folder()

    @property
    def package_src_path(self) -> Path:
        return self.src_path / self.package_folder()


def get_manager(src_path: Path = DYNAMO_ROOT) -> IDynamoManager:
    return DynamoManager(src_path)
