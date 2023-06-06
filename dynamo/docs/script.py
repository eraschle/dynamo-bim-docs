from abc import abstractmethod
from pathlib import Path
from typing import List, Optional, Sized

from dynamo.docs import custom
from dynamo.docs.doc_models import ScriptPathDocFile
from dynamo.docs.docs import IModelDocs
from dynamo.docs.manual.repository import DocsNodeFactory, DocsNodeRepository
from dynamo.docs.manual.sections import INPUT, OUTPUT
from dynamo.docs.models import content, nodes
from dynamo.docs.models.content import ADocContent, IDocContent
from dynamo.docs.models.sections import (AFileDescriptionDocs, ASectionDoc,
                                         NodeWarningSectionDocs, TutorialDocs)
from dynamo.models.files import Script
from dynamo.models.model import ICodeNode, INode
from dynamo.utils import paths


class ScriptProcessContent(ADocContent[Script]):

    def __init__(self, file_docs: DocsNodeRepository[Script], title: str) -> None:
        super().__init__(file_docs.file, children=[])
        self.title = title

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

    def has_content(self, **_) -> bool:
        return self._get_other_path() is not None

    def _content(self, level: int, **_) -> List[str]:
        return []

    def content(self, level: int, **_) -> List[str]:
        link_to_other = self._link_to_other()
        if link_to_other is None:
            raise ValueError(f'Link to other script file is None')
        return [self.title, link_to_other]

    def _get_other_path(self) -> Optional[Path]:
        number = paths.start_number_or_none_of(self.file.src_path)
        if number is None:
            return None
        files = self._files_start_with_number(self.file.src_path)
        script_idx = files.index(self.file.src_path)
        if not self._can_continue(files, script_idx):
            return None
        return files[self._get_index(script_idx)]

    def _link_to_other(self) -> Optional[str]:
        other_path = self._get_other_path()
        if other_path is None:
            return None
        next_doc = ScriptPathDocFile(other_path, self.manager)
        return self.exporter.file_link(next_doc, self.file)

    @abstractmethod
    def _can_continue(self, _: Sized, index: int) -> bool:
        pass

    @abstractmethod
    def _get_index(self, index: int) -> int:
        pass


class ScriptProcessPreviousDocs(ScriptProcessContent):

    def _can_continue(self, _: Sized, index: int) -> bool:
        return index > 0

    def _get_index(self, index: int) -> int:
        return index - 1


class ScriptProcessNextDocs(ScriptProcessContent):

    def _can_continue(self, others: Sized, index: int) -> bool:
        return index < len(others) - 1

    def _get_index(self, index: int) -> int:
        return index + 1


class ScriptInformationDocs(AFileDescriptionDocs[Script]):

    def __init__(self, file_docs: DocsNodeRepository[Script],
                 children: List[IDocContent[Script]],
                 process: List[ScriptProcessContent]) -> None:
        super().__init__(file_docs, children)
        self.process = process

    def _common_information(self, **kwargs) -> List[List[str]]:
        lines = super()._common_information()
        for child in self.process:
            if not child.has_content(**kwargs):
                continue
            lines.append(self._get_lines(
                child.content, self._lstrip_empty, **kwargs))
        return lines

    def _description(self, **_) -> List[str]:
        return self.model.description.splitlines(keepends=False)


class AInOutputSectionDocs(ASectionDoc[Script]):

    def has_content(self, **kwargs) -> bool:
        return len(self._get_nodes()) > 0

    @abstractmethod
    def _get_nodes(self) -> List[INode]:
        pass

    def _headline_content(self, **_) -> List[str]:
        return self.exporter.empty_line()

    def _docs(self, level: int, **kwargs) -> List[str]:
        node = self._get_node(INode, **kwargs)
        for child in self.children:
            if not isinstance(child, nodes.ANodeDocsContent):
                continue
            if not child.is_node(node):
                continue
            return child.content(**kwargs)
        return nodes.general_node_docs(self.file_docs).content(**kwargs)

    def _child_content(self, level: int, **kwargs) -> List[str]:
        lines = []
        for node in self._get_nodes():
            if isinstance(node, ICodeNode):
                lines.extend(self.exporter.empty_line())
                link = self.exporter.heading_link(node)
                link_content = self.exporter.heading(link, level)
                lines.extend(self.value_handler.as_list(link_content))
                continue
            content = self._get_lines(
                self._docs, level=level, node=node, **kwargs
            )
            if self._is_content(content):
                lines.extend(self.exporter.empty_line())
                lines.extend(content)
        return lines

    def _no_docs_content(self, **_) -> List[str]:
        return self.exporter.empty_line()


class InputSectionDocs(AInOutputSectionDocs):

    def __init__(self, file_docs: DocsNodeRepository[Script]) -> None:
        super().__init__(INPUT, file_docs, nodes.all_node_docs(file_docs))

    def _get_nodes(self) -> List[INode]:
        return self.model.input_nodes()


class OutputSectionDocs(AInOutputSectionDocs):

    def __init__(self, file_docs: DocsNodeRepository[Script]) -> None:
        super().__init__(OUTPUT, file_docs, nodes.all_node_docs(file_docs))

    def _get_nodes(self) -> List[INode]:
        return self.model.output_nodes()


def _scripts_content(file_docs: DocsNodeRepository[Script], with_code_block: bool) -> List[IDocContent[Script]]:
    return [
        content.title_docs(file_docs.file),
        ScriptInformationDocs(
            file_docs=file_docs,
            process=[
                ScriptProcessPreviousDocs(
                    file_docs, title='Vorheriges Skript'),
                ScriptProcessNextDocs(file_docs, title='Nächstes Skript'),
            ],
            children=[
                # SolutionOrProblemDocs(file_docs, children=[]),
                TutorialDocs(file_docs, children=[]),
                InputSectionDocs(file_docs),
                OutputSectionDocs(file_docs),
                NodeWarningSectionDocs(file_docs),
            ]
        ),
        custom.source_code_docs(file_docs, with_code_block),
        custom.dependencies_docs(file_docs),
    ]


def get_docs(file: IModelDocs[Script], with_code_block: bool):
    file_docs = DocsNodeRepository(file, factory=DocsNodeFactory())
    docs = []
    for doc_content in _scripts_content(file_docs, with_code_block):
        docs.extend(doc_content.content(1))
    file.write(docs)
