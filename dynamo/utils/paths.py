import sys
from pathlib import Path
from typing import Iterable, List, Optional, Union


def create_directory_unless_exist(path: Union[str, Path]) -> None:
    path = path if isinstance(path, Path) else Path(path)
    as_directory(path).mkdir(parents=True, exist_ok=True)


def as_directory(path: Path) -> Path:
    if len(path.suffix.strip()) > 0:
        return path.parent
    return path


def path_separator(path: Path) -> str:
    path = path.absolute()
    return '\\' if '\\' in str(path) else '/'


def path_folders(path: Path, separator: str, reverse: bool) -> List[str]:
    path = as_directory(path)
    folders = str(path).split(separator)
    if reverse:
        folders.reverse()
    return folders


def sub_path_of(root: Path, path: Path) -> List[str]:
    separator = path_separator(path)
    sub_path = str(path.absolute()).replace(str(root.absolute()), '')
    splitted = sub_path.split(separator)
    return [path for path in splitted if len(path) > 0]


def common_path_of(path: Path, other: Path) -> Path:
    path = path.absolute()
    separator = path_separator(path)
    this_folders = path_folders(path, separator, reverse=False)
    other_folders = path_folders(other, separator, reverse=False)
    folders = []
    for folder, other_folder in zip(this_folders, other_folders):
        if folder != other_folder:
            break
        folders.append(folder)
    common_path = separator.join(folders)
    return Path(common_path)


def is_sub_path_of(path: Path, other: Path) -> bool:
    return str(other.absolute()).startswith(str(path.absolute()))


def path_as_str(path: Path | str) -> str:
    return str(path).replace('\\', '/')


def relative_to(path: Path, path_to: Path) -> str:
    path_to = as_directory(path_to)
    if is_sub_path_of(path_to, path):
        relative = path.relative_to(path_to)
        return f'./{path_as_str(relative)}'
    common_path = common_path_of(path, path_to)
    path_folders = sub_path_of(common_path, path)
    to_folders = sub_path_of(common_path, path_to)
    folders = ['..' for _ in to_folders]
    folders.extend([folder for folder in path_folders])
    if folders[-1] != path.name:
        folders.append(path.name)
    relative_path = '/'.join(folders)
    return f'./{relative_path}'


def start_number_or_none_of(path: Path, separators: Iterable[str] = ['_', ' ']) -> Optional[int]:
    index = 0
    for sep in separators:
        index = path.stem.find(sep)
        if index < 1:
            continue
        number = path.stem[:index]
        try:
            return int(number)
        except:
            continue
    return None


def start_number_of(path: Path, default: int = sys.maxsize) -> int:
    number = start_number_or_none_of(path)
    return default if number is None else number


DEV_NAMES = ['_dev_', ' dev ', '-dev-']


def is_dev(path: Path) -> bool:
    return any(dev in path.stem.lower() for dev in DEV_NAMES)
