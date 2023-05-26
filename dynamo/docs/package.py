from ctypes import ArgumentError
from typing import List, Tuple

from dynamo.docs import content
from dynamo.docs.content import (AHeadingContent, AHeadingTextDocs,
                                 FileDescriptionDocs, IDocContent)
from dynamo.docs.doc_models import CustomNodeDocFile
from dynamo.docs.docs import IDocsFile, IModelDocs
from dynamo.models.files import Package


class PackageContentDocs(AHeadingTextDocs[Package]):

    def _heading_content(self, **_) -> List[str]:
        return self.values.value_or_default(self.model.info.contents, 'Keine Inhalt')


class PackageInformationDocs(AHeadingTextDocs[Package]):

    def __init__(self, file: IModelDocs[Package],
                 children: List[IDocContent[Package]],
                 heading: str) -> None:
        super().__init__(file, heading)
        self.children = children

    def _heading_content(self, **_) -> List[str]:
        lines = [
            ['Version', *self.values.value_or_default(self.model.info.version)],
            ['Engine', *self.values.value_or_default(self.model.info.engine_version)],
            ['Homepage', *self.values.value_or_default(self.model.info.site_url)],
            ['Repository', *self.values.value_or_default(self.model.info.repository_url)]
        ]
        return self.exporter.as_table(None, lines)

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_doc_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class PackageCustomNodeDocs(AHeadingContent[Package]):

    def _get_category(self, **kwargs) -> str:
        arg = 'category'
        category = kwargs.get(arg, None)
        if category is None:
            raise ArgumentError(f'Argument "{arg}" is None or does not exists')
        return category

    def _heading(self, level: int, **kwargs) -> List[str]:
        category = self._get_category(**kwargs)
        return self.exporter.heading(category, level)

    def _heading_content(self, **kwargs) -> List[str]:
        category = self._get_category(**kwargs)
        nodes = self.model.by_category(category)
        nodes = sorted(nodes, key=lambda node: node.name)
        paths: List[Tuple[IDocsFile, IDocsFile]] = [
            (CustomNodeDocFile(node, self.manager), self.file) for node in nodes
        ]
        lines = self.exporter.as_file_link_list(paths)
        return lines


class PackageNodesDocs(AHeadingTextDocs[Package]):

    def __init__(self, file: IModelDocs[Package],
                 docs: IDocContent[Package],
                 heading: str) -> None:
        super().__init__(file, heading)
        self.docs = docs

    def _categories(self) -> List[str]:
        cats = set([node.category for node in self.model.nodes])
        return sorted(cats)

    def _heading_content(self, **_) -> List[str]:
        nodes = self._categories()
        return self.values.default_if_empty(nodes, 'Keine Kategorien')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for cat in self._categories():
            content = self._get_doc_content(self.docs, level, category=cat, **kwargs)
            lines.extend(content)
        return lines


def packages_content(file: IModelDocs[Package]) -> List[IDocContent[Package]]:
    return [
        content.title_docs(file),
        PackageInformationDocs(
            file=file,
            children=[
                FileDescriptionDocs(
                    file=file, heading='Beschreibung'
                ),
                PackageContentDocs(
                    file=file, heading='Inhalt'
                )
            ],
            heading='Informationen'),
        PackageNodesDocs(
            file=file,
            docs=PackageCustomNodeDocs(file=file),
            heading='Node Dokumentationen')
    ]


def get_docs(file: IModelDocs[Package]):
    docs = []
    for package in packages_content(file):
        docs.extend(package.content(1))
    file.write(docs)
