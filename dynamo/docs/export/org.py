from typing import Any, Iterable, List, Optional, Tuple

from dynamo.docs.docs import IDocsFile, IExporter, IValueHandler
from dynamo.io.file import OrgHandler
from dynamo.utils import paths, string
from dynamo.utils.values import ValueHandler


class OrgLinkCreator:

    @classmethod
    def is_link(cls, value: str) -> bool:
        return '][' in value

    @classmethod
    def link_values(cls, value: str) -> Tuple[str, Optional[str]]:
        if not cls.is_link(value):
            raise ValueError(f'{value} is not a link')
        splitted = value.split('][')
        splitted = [string.clean_value(value) for value in splitted]
        return splitted[0], splitted[1] if len(splitted) > 1 else None

    def __init__(self, protocols: List[str]) -> None:
        self.protocols = protocols

    def _clean_link(self, link: str, default_protocol: str) -> str:
        for protocol in self.protocols:
            protocol = f'{protocol}:'
            if not link.startswith(protocol):
                continue
            return link
        return f'{default_protocol}:{link}'

    def create(self, link: str, display_name: Optional[str], default_protocol: str) -> str:
        link = self._clean_link(link, default_protocol)
        if display_name is None:
            return f'[[{link}]]'
        return f'[[{link}][{display_name}]]'


class OrgTableCreator:
    separator = '|'
    horizontal_separator = '+'

    def __init__(self, headings: List[str], rows: List[List[Any]]) -> None:
        self.headings = headings
        self.rows = rows
        self.column_size = self._column_sizes()

    def _get_column_count(self) -> int:
        column_count = 0 if self.headings is None else len(self.headings)
        for row in self.rows:
            column_count = max(column_count, len(row))
        return column_count

    def _cell_without_link(self, value: Any) -> str:
        cell = str(value)
        if OrgLinkCreator.is_link(value):
            link, display = OrgLinkCreator.link_values(value)
            cell = link if display is None else display
        return cell.strip()

    def _column_sizes(self) -> List[int]:
        sizes = [0] * self._get_column_count()
        if self.headings is not None:
            for idx, heading in enumerate(self.headings):
                sizes[idx] = max(sizes[idx], len(heading))
        for row in self.rows:
            for idx, cell in enumerate(row):
                cell_value = self._cell_without_link(cell)
                sizes[idx] = max(sizes[idx], len(cell_value))
        return sizes

    def _get_cell(self, cell: Any, index: int) -> str:
        cell = cell if isinstance(cell, str) else str(cell)
        cell = cell.strip()
        without_link = self._cell_without_link(cell)
        fill_value = ' ' * (self.column_size[index] - len(without_link))
        return f' {cell}{fill_value} '

    def _get_row(self, value: str) -> str:
        return f'{self.separator}{value}{self.separator}'

    def _create_row(self, values: List[Any]) -> str:
        row_values = [self._get_cell(value, idx) for idx, value in enumerate(values)]
        row = self.separator.join(row_values)
        return self._get_row(row)

    def _create_horizontal_line(self) -> str:
        columns = []
        for idx, heading in enumerate(self.headings):
            heading_value = self._get_cell(heading, idx)
            column = '-' * len(heading_value)
            columns.append(column)
        horizontal_line = self.horizontal_separator.join(columns)
        return self._get_row(horizontal_line)

    def create(self) -> List[str]:
        rows = []
        if self.headings is not None and len(self.headings) > 0:
            rows.append(self._create_row(self.headings))
            rows.append(self._create_horizontal_line())
        for row in self.rows:
            rows.append(self._create_row(row))
        return rows


class OrgExporter(IExporter):
    heading_prefix = "*"

    def __init__(self, file_handler: OrgHandler, value_handler: IValueHandler,
                 link_handler: OrgLinkCreator) -> None:
        super().__init__()
        self.file_handler = file_handler
        self.value_handler = value_handler
        self.link_handler = link_handler
        self._manual_lines: Optional[List[str]] = None

    def _get_preamble(self, name: str, value: str) -> str:
        name = f'{name.lower()}:'
        return f'#+{name:<15}{value.strip()}'

    def doc_head(self) -> List[str]:
        return [
            self._get_preamble(
                'Setupfile', 'https://fniessen.github.io/org-html-themes/org/theme-readtheorg.setup'),
            self._get_preamble(
                'html_head', '<style>pre.src{background:#343131;color:white;} </style>')
        ]

    def empty_line(self, amount: int = 1) -> List[str]:
        return self.value_handler.empty_line(amount)

    def title(self, file: IDocsFile):
        return [self._get_preamble("Title", file.display_name)]

    def heading(self, name: str, level: int) -> List[str]:
        prefix = self.heading_prefix * level
        return [f'{prefix} {name}']

    def is_heading(self, value: str) -> bool:
        if value.startswith(' '):
            value = value.lstrip()
        splitted = value.split(' ')
        if len(splitted) < 2:
            return False
        first = splitted[0].strip()
        level_prefix = self.heading_prefix * len(first)
        return first == level_prefix

    def _as_list_line(self, value: str, symbol: str, indent: int) -> str:
        indent_str = '' if indent <= 0 else ' ' * indent
        return f'{indent_str}{symbol} {value}'

    def as_list(self, values: Iterable[str], level: int = 0, symbol: str = '-') -> List[str]:
        return [self._as_list_line(value, symbol, level) for value in values]

    def url_link(self, url: str, display_name: Optional[str]) -> List[str]:
        return [self.link_handler.create(url, display_name, 'https')]

    def file_link(self, file: IDocsFile, relative_to: IDocsFile) -> str:
        relative = paths.relative_to(file.doc_path, relative_to.doc_path)
        return self.link_handler.create(relative, file.display_name, 'file')

    def link_indexes(self, lines: List[str]) -> List[Tuple[int, str, Optional[str]]]:
        indexes = []
        for idx, line in enumerate(lines):
            if not OrgLinkCreator.is_link(line):
                continue
            value = idx, *OrgLinkCreator.link_values(line)
            indexes.append(value)
        return indexes

    def _file_link_list(self, values: Iterable[Tuple[IDocsFile, IDocsFile]]) -> List[str]:
        file_links = []
        for value in values:
            link = self.file_link(*value)
            file_links.append(link)
        return file_links

    def as_file_link_list(self, values: Iterable[Tuple[IDocsFile, IDocsFile]]) -> List[str]:
        file_links = self._file_link_list(values)
        return self.as_list(file_links)

    def as_table(self, heading: List[str], lines: List[List[Any]]) -> List[str]:
        creator = OrgTableCreator(heading, lines)
        return creator.create()

    def _table_end(self, start_index: int, lines: List[str]) -> int:
        for idx in range(start_index, len(lines)):
            if lines[idx].startswith(OrgTableCreator.separator):
                continue
            return idx
        return len(lines)

    def table_ranges(self, lines: List[str]) -> List[Tuple[int, int]]:
        idx = 0
        ranges = []
        while idx < len(lines):
            line = lines[idx].lstrip()
            if not line.startswith(OrgTableCreator.separator):
                idx += 1
                continue
            end_idx = self._table_end(idx, lines)
            ranges.append((idx, end_idx))
            idx = end_idx
        return ranges

    def _get_code_line(self, code: str, indent: int) -> str:
        indent_str = ' ' * indent
        code = code.replace('\t', indent_str)
        return code.rstrip()

    def as_code(self, code: str, language: str, indent: int) -> List[str]:
        code_lines = [f'#+begin_src {language}']
        for code_line in code.splitlines(keepends=False):
            line = self._get_code_line(code_line, indent)
            code_lines.append(line)
        code_lines.append('#+end_src')
        return code_lines


def get_org_exporter() -> IExporter:
    file_handler = OrgHandler()
    value_handler = ValueHandler()
    link_handler = OrgLinkCreator(['file', 'http', 'https'])
    return OrgExporter(file_handler=file_handler, value_handler=value_handler, link_handler=link_handler)
