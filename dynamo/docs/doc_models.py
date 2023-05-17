from abc import abstractmethod
from pathlib import Path
from typing import List, Optional

from dynamo.docs.docs import IDocsFile, IDocsManager, IModelDocs, TModel
from dynamo.models.files import CustomFileNode, Package, Script
from dynamo.models.model import IPackage
from dynamo.utils import paths, string


def _with_clean_file_name(src_path: Path) -> Path:
    file_name = string.clean_value(src_path.stem)
    return src_path.with_stem(file_name)


class ADocFile(IDocsFile):

    def __init__(self, manager: IDocsManager) -> None:
        super().__init__()
        self.manager = manager
        self._doc_path: Optional[Path] = None
        self._existing_docs: Optional[List[str]] = None

    @property
    @abstractmethod
    def src_path(self) -> Path:
        pass

    @property
    def doc_path(self) -> Path:
        if self._doc_path is None:
            doc_path = self._switch_and_clean_file_name(self.src_path)
            self._doc_path = self._get_doc_path(doc_path)
        return self._doc_path

    @property
    def display_name(self) -> str:
        src_path = _with_clean_file_name(self.src_path)
        return string.replace_with_space(src_path.stem)

    def _switch_and_clean_file_name(self, src_path: Path) -> Path:
        src_path = _with_clean_file_name(src_path)
        return self.manager.switch_path(src_path)

    def _get_doc_path(self, doc_path: Path) -> Path:
        return doc_path

    def existing_docs(self) -> List[str]:
        if self._existing_docs is None:
            handler = self.manager.exporter.handler
            self._existing_docs = []
            if handler.can_read(self.doc_path):
                self._existing_docs = handler.read(self.doc_path)
        return self._existing_docs


class AModelDocFile(ADocFile, IModelDocs[TModel]):

    def __init__(self, model: TModel, manager: IDocsManager) -> None:
        super().__init__(manager)
        self.model = model

    @property
    def src_path(self) -> Path:
        return self.model.path

    def write(self, lines: List[str]):
        handler = self.manager.exporter.handler
        paths.create_directory_unless_exist(self.doc_path)
        handler.write(self.doc_path, lines)


def _package_path(package: IPackage, manager: IDocsManager, with_version: bool) -> Path:
    package_path = manager.package_doc_path / package.name
    return package_path / package.version if with_version else package_path


class PackageDocFile(AModelDocFile[Package]):

    @property
    def display_name(self) -> str:
        return string.replace_with_space(self.model.full_name)

    def _get_doc_path(self, doc_path: Path) -> Path:
        path = _package_path(self.model, self.manager, with_version=False)
        name = string.clean_value(self.model.name)
        version = string.clean_value(self.model.version)
        file_name = f'{name}-{version}'
        doc_path = doc_path.with_stem(file_name)
        return path / doc_path.name


class CustomNodeDocFile(AModelDocFile[CustomFileNode]):

    def _get_doc_path(self, doc_path: Path) -> Path:
        package = self.model.package
        package_path = _package_path(package, self.manager, with_version=True)
        return package_path / doc_path.name


class ScriptDocFile(AModelDocFile[Script]):
    pass


class ScriptPathDocFile(ADocFile):

    def __init__(self, path: Path, manager: IDocsManager) -> None:
        super().__init__(manager)
        self._path = path

    @property
    def src_path(self) -> Path:
        return self._path
