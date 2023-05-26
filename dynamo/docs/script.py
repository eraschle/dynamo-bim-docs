from abc import abstractmethod
from pathlib import Path
from typing import List, Optional, Sized

from dynamo.docs import content, custom
from dynamo.docs.content import (ASectionDoc, FileAndDirectoryDocs,
                                 FilesAndDirectoriesDocs, IDocContent,
                                 SolutionOrProblemDocs, TutorialDocs)
from dynamo.docs.doc_models import ScriptPathDocFile
from dynamo.docs.docs import IModelDocs
from dynamo.docs.docs_parser import (DOCS, FILES, INPUT, OUTPUT, SOLUTION,
                                     DocsNodeFactory, DocsNodeRepository)
from dynamo.models.files import Script
from dynamo.utils import paths


class ScriptInputOutputContent(ASectionDoc[Script]):

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
        lines = self.exporter.value_handler.strip_starting_empty(lines)
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

    def _can_continue(self, _: Sized, index: int) -> bool:
        return index > 0

    def _get_index(self, index: int) -> int:
        return index - 1


class ScriptOutputDocs(ScriptInputOutputContent):

    def _can_continue(self, others: Sized, index: int) -> bool:
        return index < len(others) - 1

    def _get_index(self, index: int) -> int:
        return index + 1


def _scripts_content(file_docs: DocsNodeRepository[Script]) -> List[IDocContent[Script]]:
    return [
        content.title_docs(file_docs.file),
        TutorialDocs(
            section=DOCS, file_docs=file_docs,
            children=[
                SolutionOrProblemDocs(
                    section=SOLUTION, file_docs=file_docs
                ),
                FilesAndDirectoriesDocs(
                    section=FILES, file_docs=file_docs,
                    node_docs=FileAndDirectoryDocs(file_docs)
                ),
                ScriptOutputDocs(
                    section=OUTPUT, file_docs=file_docs
                ),
                ScriptInputDocs(
                    section=INPUT, file_docs=file_docs
                )
            ]
        ),
        custom.source_code_docs(file_docs, with_code_block=True),
        custom.information_docs(file_docs),
    ]


def get_docs(file: IModelDocs[Script]):
    file_docs = DocsNodeRepository(file, factory=DocsNodeFactory())
    docs = []
    for doc_content in _scripts_content(file_docs):
        docs.extend(doc_content.content(1))
    file.write(docs)
