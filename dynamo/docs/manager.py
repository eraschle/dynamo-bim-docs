from pathlib import Path
from typing import Optional

from dynamo.docs.doc_models import CustomNodeDocFile
from dynamo.docs.docs import IDocsFile, IDocsManager, IExporter
from dynamo.docs.export.org import get_org_exporter
from dynamo.models.model import ICustomNode
from dynamo.service.dynamo import DOC_ROOT
from dynamo.service.protocol import IDynamoManager


def _get_doc_path(src: Path, dest: Path, current: Path) -> Path:
    sub_path = str(current.absolute()).replace(str(src.absolute()), '')
    if sub_path.startswith('/') or sub_path.startswith('\\'):
        sub_path = sub_path[1:]
    return dest / sub_path


class DynamoDocManager(IDocsManager):

    def __init__(self, doc_path: Path, manager: IDynamoManager, exporter: IExporter) -> None:
        super().__init__()
        self._doc_path = doc_path
        self.exporter = exporter
        self._manager = manager

    @property
    def doc_root(self) -> Path:
        return self._doc_path

    @property
    def script_src_path(self) -> Path:
        return self._manager.script_src_path

    @property
    def script_doc_path(self) -> Path:
        return self._doc_path / self._manager.script_folder()

    @property
    def package_src_path(self) -> Path:
        return self._manager.package_src_path

    @property
    def package_doc_path(self) -> Path:
        return self._doc_path / self._manager.package_folder()

    def switch_path(self, path: Path) -> Path:
        src_path = str(path.absolute())
        if src_path.startswith(str(self.script_src_path)):
            dest_path = _get_doc_path(self.script_src_path, self.script_doc_path, path)
        else:
            dest_path = _get_doc_path(self.package_src_path, self.package_doc_path, path)
        return dest_path.with_suffix(self.exporter.file_handler.extension)

    def doc_file_of(self, node: ICustomNode) -> Optional[IDocsFile]:
        file_node = self._manager.get(node)
        if file_node is None:
            return None
        return CustomNodeDocFile(file_node, self)


def create_docs(manager: IDynamoManager, doc_root: Path = DOC_ROOT, exporter: IExporter = get_org_exporter()) -> IDocsManager:
    return DynamoDocManager(doc_root, manager, exporter)
