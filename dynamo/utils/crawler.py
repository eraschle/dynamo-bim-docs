import concurrent.futures
from abc import ABC
from pathlib import Path
from typing import Iterable, List, Protocol

from dynamo.utils import checks


class ICrawleOptions(Protocol):

    def is_crawling_allowed(self, path: Path) -> bool:
        ...

    def can_append(self, path: Path) -> bool:
        ...


def _crawle(current: Path, options: ICrawleOptions) -> List[Path]:
    entries = []
    for entry in current.iterdir():
        if entry.is_dir():
            if options.can_append(entry):
                entries.append(entry)
            if options.is_crawling_allowed(entry):
                entries.extend(_crawle(entry, options))
        elif options.can_append(entry):
            entries.append(entry)
    return entries


def crawling(roots: Iterable[Path], options: ICrawleOptions) -> List[Path]:
    entries = []
    for root in roots:
        entries.extend(_crawle(root, options))
    return entries


def async_crawling(roots: Iterable[Path], options: ICrawleOptions) -> List[Path]:
    folders = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        task = {executor.submit(_crawle, root, options): root for root in roots}
        for future in concurrent.futures.as_completed(task):
            root_folder = task[future]
            try:
                folder = future.result()
                folders.extend(folder)
            except Exception as exc:
                print('%r Exception: %s' % (root_folder, exc))
    return folders



class ACrawleOption(ABC, ICrawleOptions):
    def __init__(self, extensions: List[str]) -> None:
        super().__init__()
        self.extensions = [ext if ext.startswith('.') else f'.{ext}' for ext in extensions]

    def is_crawling_allowed(self, path: Path) -> bool:
        return True

    def can_append(self, path: Path) -> bool:
        return path.suffix in self.extensions


class ExtensionCrawleOption(ACrawleOption):
    excluded_contains = [
        'DEV'
    ]

    excluded_equals = [
        'backup', 'Archiv', 'alt', 'old'
    ]

    excluded_starts = [
        '_', '-'
    ]


    def is_excluded_contains(self, path: Path) -> bool:
        return any(value in path.stem for value in self.excluded_contains)
    def is_excluded_equals(self, path: Path) -> bool:
        return any(path.stem.lower() == value for value in self.excluded_equals)

    def is_excluded_starts(self, path: Path) -> bool:
        return any(path.stem.startswith(value) for value in self.excluded_starts)

    def is_crawling_allowed(self, path: Path) -> bool:
        return (not self.is_excluded_starts(path)
                and not self.is_excluded_equals(path)
                and not self.is_excluded_contains(path))

    def can_append(self, path: Path) -> bool:
        if checks.is_none_or_empty(path.suffix) or path.is_dir():
            return False
        if self.is_excluded_contains(path):
            return False
        return super().can_append(path)


class RemoveExtensionCrawleOption(ExtensionCrawleOption):

    def is_crawling_allowed(self, path: Path) -> bool:
        return True

    def can_append(self, path: Path) -> bool:
        return True


