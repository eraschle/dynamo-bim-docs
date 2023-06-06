from typing import List, TypeVar

from dynamo.docs.docs import IModelDocs
from dynamo.docs.manual.repository import DocsNodeFactory, DocsNodeRepository
from dynamo.docs.models import content
from dynamo.docs.models.headlines import (CodeBlocksDocs, DependenciesDocs,
                                          ExternalDependenciesDocs,
                                          PackageDependenciesDocs,
                                          PythonNodesDocs, SourceCodeDocs)
from dynamo.docs.models.nodes import (CodeBlockDoc, ExternalDependencyDocs,
                                      IDocContent, PackageDependencyDocs,
                                      PythonNodeDoc)
from dynamo.docs.models.sections import AFileDescriptionDocs, IDocContent
from dynamo.models.files import ADynamoFileNode, CustomFileNode

TDynamo = TypeVar('TDynamo', bound=ADynamoFileNode)


def source_code_docs(file_docs: DocsNodeRepository[TDynamo], with_code_block: bool) -> IDocContent[TDynamo]:
    children: List[IDocContent[TDynamo]] = [
        PythonNodesDocs(
            file=file_docs.file, headline='Python Nodes',
            children=[PythonNodeDoc(file_docs, children=[])],
        )
    ]
    if with_code_block:
        children.append(
            CodeBlocksDocs(
                file=file_docs.file, headline='Code Blocks',
                children=[CodeBlockDoc(file_docs, children=[])],

            )
        )
    return SourceCodeDocs(
        file=file_docs.file, children=children, headline='Source Code'
    )


def dependencies_docs(file_docs: DocsNodeRepository[TDynamo]) -> IDocContent[TDynamo]:
    return DependenciesDocs(
        file=file_docs.file, headline='Abhängigkeiten',
        children=[
            PackageDependenciesDocs(
                file=file_docs.file, headline='Packages',
                children=[
                    PackageDependencyDocs(file_docs=file_docs, children=[])
                ],
            ),
            ExternalDependenciesDocs(
                file=file_docs.file, headline='External',
                children=[
                    ExternalDependencyDocs(file_docs=file_docs, children=[])
                ],
            )
        ]
    )


class CustomNodeInformationDocs(AFileDescriptionDocs[CustomFileNode]):

    def _common_information(self) -> List[List[str]]:
        lines = super()._common_information()
        lines.append(
            ['Kategorie', self.value_handler.as_str(self.model.category)])
        return lines

    def _description(self, **_) -> List[str]:
        return self.model.description.splitlines(keepends=False)


def _custom_content(file_docs: DocsNodeRepository[CustomFileNode], with_code_block: bool) -> List[IDocContent[CustomFileNode]]:
    return [
        content.title_docs(file_docs.file),
        CustomNodeInformationDocs(file_docs=file_docs, children=[]),
        source_code_docs(file_docs=file_docs, with_code_block=with_code_block),
        dependencies_docs(file_docs=file_docs),
    ]


def get_docs(file: IModelDocs[CustomFileNode], with_code_block: bool):
    file_docs = DocsNodeRepository(file, factory=DocsNodeFactory())
    lines = []
    for content in _custom_content(file_docs, with_code_block):
        lines.extend(content.content(1))
    file.write(lines)
