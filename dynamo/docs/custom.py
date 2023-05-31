from typing import List, TypeVar

from dynamo.docs.docs import IModelDocs
from dynamo.docs.manual.models import DESCRIPTION, INFO
from dynamo.docs.manual.parser import DocsNodeFactory, DocsNodeRepository
from dynamo.docs.models import content
from dynamo.docs.models.nodes import (ACodeNodesDocs, CodeBlockDoc,
                                      CodeBlocksDocs, DependenciesDocs,
                                      ExternalDependenciesDocs,
                                      ExternalDependencyDocs, IDocContent,
                                      PackageDependenciesDocs,
                                      PackageDependencyDocs, PythonNodeDoc,
                                      PythonNodesDocs, SourceCodeDocs)
from dynamo.docs.models.sections import (FileDescriptionDocs,
                                         FileInformationDocs, IDocContent)
from dynamo.models.files import ADynamoFileNode, CustomFileNode

TDynamo = TypeVar('TDynamo', bound=ADynamoFileNode)


def information_docs(file_docs: DocsNodeRepository[TDynamo]) -> IDocContent[TDynamo]:
    return FileInformationDocs(
        section=INFO, file_docs=file_docs,
        children=[
            FileDescriptionDocs(
                section=DESCRIPTION, file_docs=file_docs
            ),
            DependenciesDocs(
                file=file_docs.file, headline='Abhängigkeiten',
                children=[
                    PackageDependenciesDocs(
                        file=file_docs.file, headline='Packages',
                        node_docs=PackageDependencyDocs(file_docs),
                    ),
                    ExternalDependenciesDocs(
                        file=file_docs.file, headline='External',
                        node_docs=ExternalDependencyDocs(file_docs),
                    )
                ]
            )
        ]
    )


def source_code_docs(file_docs: DocsNodeRepository[TDynamo], with_code_block: bool) -> IDocContent[TDynamo]:
    children: List[ACodeNodesDocs[TDynamo]] = [
        PythonNodesDocs(
            file=file_docs.file, headline='Python Nodes',
            code_docs=PythonNodeDoc(file_docs),
        )
    ]
    if with_code_block:
        children.append(
            CodeBlocksDocs(
                file=file_docs.file, headline='Code Blocks',
                code_docs=CodeBlockDoc(file_docs),

            )
        )
    return SourceCodeDocs(
        file=file_docs.file, children=children, headline='Source Code'
    )


def _custom_content(file_docs: DocsNodeRepository[CustomFileNode]) -> List[IDocContent[CustomFileNode]]:
    return [
        content.title_docs(file_docs.file),
        source_code_docs(file_docs=file_docs, with_code_block=False),
        information_docs(file_docs=file_docs),
    ]


def get_docs(file: IModelDocs[CustomFileNode]):
    file_docs = DocsNodeRepository(file, factory=DocsNodeFactory())
    lines = []
    for content in _custom_content(file_docs):
        lines.extend(content.content(1))
    file.write(lines)
