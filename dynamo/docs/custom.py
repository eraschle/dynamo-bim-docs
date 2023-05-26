from typing import List, TypeVar

from dynamo.docs import content
from dynamo.docs.content import (CodeBlockDocs, CodeBlocksDocs,
                                 DependenciesDocs, ExternalDependenciesDocs,
                                 ExternalDependencyDocs, FileDescriptionDocs,
                                 FileInformationDocs, IDocContent,
                                 PackageDependenciesDocs,
                                 PackageDependencyDocs, PythonNodeDocs,
                                 PythonNodesDocs, SourceCodeDocs)
from dynamo.docs.docs import IModelDocs
from dynamo.models.files import ADynamoFileNode, CustomFileNode

TDynamo = TypeVar('TDynamo', bound=ADynamoFileNode)


def information_docs(file: IModelDocs[TDynamo]) -> IDocContent[TDynamo]:
    return FileInformationDocs(
        file=file,
        children=[
            FileDescriptionDocs(
                file=file,
                heading='Beschreibung'
            ),
            DependenciesDocs(
                file=file,
                children=[
                    PackageDependenciesDocs(
                        file=file,
                        node_docs=PackageDependencyDocs(file=file),
                        heading='Packages'
                    ),
                    ExternalDependenciesDocs(
                        file=file,
                        node_docs=ExternalDependencyDocs(file=file),
                        heading='External'
                    )
                ],
                heading='Abhängigkeiten'
            )
        ],
        heading='Informationen')


def source_code_docs(file: IModelDocs[TDynamo], with_code_block: bool) -> IDocContent[TDynamo]:
    children: List[IDocContent[TDynamo]] = [
        PythonNodesDocs(
            file=file, node_docs=PythonNodeDocs(file), heading='Python Nodes'
        )
    ]
    if with_code_block:
        children.append(
            CodeBlocksDocs(
                file=file, node_docs=CodeBlockDocs(file=file), heading='Code Blocks'
            )
        )
    return SourceCodeDocs(file=file, children=children, heading='Source Code')


def _custom_content(file: IModelDocs[CustomFileNode]) -> List[IDocContent[CustomFileNode]]:
    return [
        content.title_docs(file),
        source_code_docs(file, with_code_block=False),
        information_docs(file),
    ]


def get_docs(file: IModelDocs[CustomFileNode]):
    lines = []
    for content in _custom_content(file):
        lines.extend(content.content(1))
    file.write(lines)
