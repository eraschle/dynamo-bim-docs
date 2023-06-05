from ctypes import ArgumentError
from typing import List, Tuple

from dynamo.docs.doc_models import CustomNodeDocFile
from dynamo.docs.docs import IDocsFile, IModelDocs
from dynamo.docs.models import content
from dynamo.docs.models.content import IDocContent
from dynamo.docs.models.headlines import AHeadlineDoc
from dynamo.models.files import Package


class PackageContentDocs(AHeadlineDoc[Package]):

    def has_content(self, **kwargs) -> bool:
        return super().has_content(**kwargs)

    def _headline_content(self, **_) -> List[str]:
        return self.value_handler.as_list(self.model.info.contents, 'Keine Inhalt')


class PackageDescriptionDocs(AHeadlineDoc[Package]):

    def _headline_content(self, **_) -> List[str]:
        return self.value_handler.as_list(self.model.description, 'Keine Beschreibung')


class PackageInformationDocs(AHeadlineDoc[Package]):

    def _headline_content(self, **_) -> List[str]:
        info = self.model.info
        default_value = 'Keine Angaben'
        lines = [
            ['Version', self.value_handler.as_str(info.version, default_value)],
            ['Dynamo-Engine', self.value_handler.as_str(info.engine_version, default_value)],
            ['Homepage', self.value_handler.as_str(info.site_url, default_value)],
            ['Repository', self.value_handler.as_str(info.repository_url, default_value)]
        ]
        return self.exporter.as_table(None, lines)


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

    def _categories(self) -> List[str]:
        cats = set([node.category for node in self.model.nodes])
        return sorted(cats)

    def _headline_content(self, **_) -> List[str]:
        nodes = self._categories()
        return self.value_handler.default_if_empty(nodes, 'Keine Kategorien')

    def _child_doc(self, **kwargs) -> List[str]:
        return self.children[0].content(**kwargs)

    def _child_content(self, level: int, **kwargs) -> List[str]:
        lines = []
        for cat in self._categories():
            content = self._get_lines(self._child_doc, level=level, category=cat, **kwargs)
            lines.extend(content)
        return lines


def packages_content(file: IModelDocs[Package]) -> List[IDocContent[Package]]:
    return [
        content.title_docs(file),
        PackageInformationDocs(
            file=file,
            children=[
                PackageDescriptionDocs(
                    file=file, headline='Beschreibung', children=[]
                ),
                PackageContentDocs(
                    file=file, headline='Inhalt', children=[]
                )
            ],
            headline='Informationen'),
        PackageNodesDocs(
            file=file, headline='Node Dokumentationen',
            children=[PackageCustomNodeDocs(file=file, children=[], headline='')])
    ]


def get_docs(file: IModelDocs[Package]):
    docs = []
    for package in packages_content(file):
        docs.extend(package.content(1))
    file.write(docs)
