from abc import abstractmethod
from pathlib import Path
from typing import List, Optional, Sized

from dynamo.docs import content, custom
from dynamo.docs.content import (AHeadingTextDocs, FileAndDirectoryDocs,
                                 FilesAndDirectoriesDocs, IDocContent,
                                 SolutionOrProblemDocs, TutorialDocs)
from dynamo.docs.doc_models import ScriptPathDocFile
from dynamo.docs.docs import IModelDocs
from dynamo.models.files import Script
from dynamo.utils import paths


class ScriptInputOutputContent(AHeadingTextDocs[Script]):

    def _files_start_with_number(self, src_file: Path) -> List[Path]:
        files = []
        for path in src_file.parent.glob(f'*{src_file.suffix}'):
            if paths.is_dev(path):
                continue
            number = paths.start_number_or_none_of(path)
            if number is None:
                continue
            files.append(path)
        return sorted(files, key=lambda path: paths.start_number_of(path))

    def _clean_existing_content(self) -> List[str]:
        lines = super()._clean_existing_content()
        indexes = self.exporter.link_indexes(lines)
        if len(indexes) == 0:
            return lines
        index, link, _ = indexes[0]
        if link.endswith(self.file.doc_path.suffix):
            del lines[index]
        lines = self.values.strip_starting_empty(lines)
        return lines

    def _heading_content(self, **kwargs) -> List[str]:
        lines = []
        link_to_other = self._link_to_other()
        if link_to_other is not None:
            lines.append(link_to_other)
            lines.extend(self.exporter.empty_line())
        lines.extend(self._manual_docs())
        return lines

    def _link_to_other(self) -> Optional[str]:
        number = paths.start_number_or_none_of(self.file.src_path)
        if number is None:
            return None
        files = self._files_start_with_number(self.file.src_path)
        script_idx = files.index(self.file.src_path)
        if not self._can_continue(files, script_idx):
            return None
        other_path = files[self._get_index(script_idx)]
        next_doc = ScriptPathDocFile(other_path, self.manager)
        return self.exporter.file_link(next_doc, self.file)

    @abstractmethod
    def _can_continue(self, _: Sized, index: int) -> bool:
        pass

    @abstractmethod
    def _get_index(self, index: int) -> int:
        pass


class ScriptInputDocs(ScriptInputOutputContent):

    def __init__(self, file: IModelDocs[Script], heading: str) -> None:
        super().__init__(file, heading)

    def _can_continue(self, _: Sized, index: int) -> bool:
        return index > 0

    def _get_index(self, index: int) -> int:
        return index - 1


class ScriptOutputDocs(ScriptInputOutputContent):

    def __init__(self, file: IModelDocs[Script], heading: str) -> None:
        super().__init__(file, heading)

    def _can_continue(self, others: Sized, index: int) -> bool:
        return index < len(others) - 1

    def _get_index(self, index: int) -> int:
        return index + 1


def _scripts_content(file: IModelDocs[Script]) -> List[IDocContent[Script]]:
    return [
        content.title_docs(file),
        TutorialDocs(
            file=file,
            children=[
                SolutionOrProblemDocs(
                    file=file,
                    heading='Problem / Lösung'
                ),
                FilesAndDirectoriesDocs(
                    file=file,
                    node_docs=FileAndDirectoryDocs(file=file),
                    heading='Dateien / Verzeichnisse'
                ),
                ScriptInputDocs(
                    file=file,
                    heading='Eingabe'
                ),
                ScriptOutputDocs(
                    file=file,
                    heading='Ausgabe'
                ),
            ],
            heading='Anleitung'
        ),
        custom.source_code_docs(file, with_code_block=True),
        custom.information_docs(file),
    ]


def get_docs(file: IModelDocs[Script]):
    docs = []
    for doc_content in _scripts_content(file):
        docs.extend(doc_content.content(1))
    file.write(docs)
