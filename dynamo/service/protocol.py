from pathlib import Path
from typing import Optional, Protocol

from dynamo.models.files import CustomFileNode, Package
from dynamo.models.model import ICustomNode


class IDynamoManager(Protocol):

    @classmethod
    def script_folder(cls) -> str:
        ...

    @classmethod
    def package_folder(cls) -> str:
        ...

    @property
    def script_src_path(self) -> Path:
        ...

    @property
    def package_src_path(self) -> Path:
        ...

    def add(self, package: Package):
        ...

    def get(self, node: ICustomNode) -> Optional[CustomFileNode]:
        ...
