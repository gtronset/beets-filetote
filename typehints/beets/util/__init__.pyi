from collections.abc import Iterable, Iterator, Sequence
from enum import Enum
from logging import Logger
from pathlib import Path
from re import Pattern
from typing import Any, TypeAlias, TypeVar

StrPath: TypeAlias = str | Path
PathLike: TypeAlias = StrPath | bytes
Bytes_or_String: TypeAlias = str | bytes
_AnyStr = TypeVar("_AnyStr", str, bytes)

def ancestry(path: _AnyStr) -> list[_AnyStr]: ...
def displayable_path(
    path: PathLike | Iterable[PathLike], separator: str = "; "
) -> str: ...
def normpath(path: PathLike) -> bytes: ...
def sanitize_path(
    path: str,
    replacements: Sequence[Sequence[Pattern[Any] | str]] | None = None,
) -> str: ...
def unique_path(path: _AnyStr) -> _AnyStr: ...
def bytestring_path(path: PathLike) -> bytes: ...
def mkdirall(path: _AnyStr) -> None: ...
def syspath(path: PathLike, prefix: bool = True) -> str: ...
def copy(path: PathLike, dest: PathLike, replace: bool = False) -> None: ...
def move(path: PathLike, dest: PathLike, replace: bool = False) -> None: ...
def link(path: PathLike, dest: PathLike, replace: bool = False) -> None: ...
def reflink(
    path: PathLike,
    dest: PathLike,
    replace: bool = False,
    fallback: bool = False,
) -> None: ...
def hardlink(path: PathLike, dest: PathLike, replace: bool = False) -> None: ...
def prune_dirs(
    path: PathLike,
    root: PathLike | None = None,
    clutter: Sequence[str] = (".DS_Store", "Thumbs.db"),
) -> None: ...
def sorted_walk(
    path: _AnyStr,
    ignore: Sequence[_AnyStr] = (),
    ignore_hidden: bool = False,
    logger: Logger | None = None,
) -> Iterator[tuple[_AnyStr, Sequence[_AnyStr], Sequence[_AnyStr]]]: ...

class MoveOperation(Enum):
    MOVE = 0
    COPY = 1
    LINK = 2
    HARDLINK = 3
    REFLINK = 4
    REFLINK_AUTO = 5

class FilesystemError(Exception):
    paths: Sequence[PathLike]

    def __init__(
        self,
        reason: str | Exception,
        verb: str,
        paths: Sequence[PathLike],
        tb: str | None = None,
    ) -> None: ...
    def get_message(self) -> str: ...
