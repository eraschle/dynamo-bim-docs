from ctypes import ArgumentError
from typing import List, Tuple

from dynamo.docs.doc_models import CustomNodeDocFile
from dynamo.docs.docs import IDocsFile, IModelDocs
from dynamo.docs.models import content
from dynamo.docs.models.content import AHeadlineDoc, IDocContent
from dynamo.models.files import Package


class PackageContentDocs(AHeadlineDoc[Package]):

    def _headline_content(self, **_) -> List[str]:
        return self.value_handler.as_list(self.model.info.contents, 'Keine Inhalt')


class PackageDescriptionDocs(AHeadlineDoc[Package]):

    def _headline_content(self, **_) -> List[str]:
        return self.value_handler.as_list(self.model.description, 'Keine Beschreibung')


class PackageInformationDocs(AHeadlineDoc[Package]):

    def __init__(self, file: IModelDocs[Package],
                 children: List[IDocContent[Package]],
                 headline: str) -> None:
        super().__init__(file, headline)
        self.children = children

    def _headline_content(self, **_) -> List[str]:
        lines = [
            ['Version', *self.value_handler.as_str(self.model.info.version)],
            ['Engine', *self.value_handler.as_str(self.model.info.engine_version)],
            ['Homepage', *self.value_handler.as_str(self.model.info.site_url)],
            ['Repository', *self.value_handler.as_str(self.model.info.repository_url)]
        ]
        return self.exporter.as_table(None, lines)

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for child in self.children:
            content = self._get_content(child, level, **kwargs)
            lines.extend(content)
        return lines


class PackageCustomNodeDocs(AHeadlineDoc[Package]):

    def _get_category(self, **kwargs) -> str:
        arg = 'category'
        category = kwargs.get(arg, None)
        if category is None:
            raise ArgumentError(f'Argument "{arg}" is None or does not exists')
        return category

    def _headline(self, level: int, **kwargs) -> List[str]:
        category = self._get_category(**kwargs)
        return self.exporter.heading(category, level)

    def _headline_content(self, **kwargs) -> List[str]:
        category = self._get_category(**kwargs)
        nodes = self.model.by_category(category)
        nodes = sorted(nodes, key=lambda node: node.name)
        paths: List[Tuple[IDocsFile, IDocsFile]] = [
            (CustomNodeDocFile(node, self.manager), self.file) for node in nodes
        ]
        lines = self.exporter.as_file_link_list(paths)
        return lines


class PackageNodesDocs(AHeadlineDoc[Package]):

    def __init__(self, file: IModelDocs[Package],
                 docs: IDocContent[Package],
                 headline: str) -> None:
        super().__init__(file, headline)
        self.docs = docs

    def _categories(self) -> List[str]:
        cats = set([node.category for node in self.model.nodes])
        return sorted(cats)

    def _headline_content(self, **_) -> List[str]:
        nodes = self._categories()
        return self.value_handler.default_if_empty(nodes, 'Keine Kategorien')

    def _children_content(self, level: int, **kwargs) -> List[str]:
        lines = super()._children_content(level, **kwargs)
        for cat in self._categories():
            content = self._get_content(self.docs, level, category=cat, **kwargs)
            lines.extend(content)
        return lines


def packages_content(file: IModelDocs[Package]) -> List[IDocContent[Package]]:
    return [
        content.title_docs(file),
        PackageInformationDocs(
            file=file,
            children=[
                PackageDescriptionDocs(
                    file=file, headline='Beschreibung'
                ),
                PackageContentDocs(
                    file=file, headline='Inhalt'
                )
            ],
            headline='Informationen'),
        PackageNodesDocs(
            file=file,
            docs=PackageCustomNodeDocs(file=file, headline=''),
            headline='Node Dokumentationen')
    ]


def get_docs(file: IModelDocs[Package]):
    docs = []
    for package in packages_content(file):
        docs.extend(package.content(1))
    file.write(docs)
