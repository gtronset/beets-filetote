from collections.abc import Generator, Sequence
from enum import Enum
from logging import Logger
from re import Pattern
from typing import Any, AnyStr

from typing_extensions import TypeAlias

Bytes_or_String: TypeAlias = str | bytes

def ancestry(path: Bytes_or_String) -> list[Bytes_or_String]: ...
def displayable_path(
    path: Bytes_or_String | tuple[Bytes_or_String, ...],
    separator: str = "; ",
) -> str: ...
def normpath(path: bytes) -> bytes: ...
def sanitize_path(
    path: str,
    replacements: Sequence[Sequence[Pattern[Any] | str]] | None = None,
) -> str: ...
def unique_path(path: bytes) -> bytes: ...
def bytestring_path(path: Bytes_or_String) -> bytes: ...
def mkdirall(path: bytes) -> None: ...
def syspath(path: bytes, prefix: bool = True) -> Bytes_or_String: ...
def copy(path: bytes, dest: bytes, replace: bool = False) -> None: ...
def move(path: bytes, dest: bytes, replace: bool = False) -> None: ...
def link(path: bytes, dest: bytes, replace: bool = False) -> None: ...
def reflink(
    path: bytes,
    dest: bytes,
    replace: bool = False,
    fallback: bool = False,
) -> None: ...
def hardlink(path: bytes, dest: bytes, replace: bool = False) -> None: ...
def prune_dirs(
    path: bytes,
    root: Bytes_or_String | None = None,
    clutter: Sequence[str] = (".DS_Store", "Thumbs.db"),
) -> None: ...
def sorted_walk(
    path: AnyStr,
    ignore: Sequence[Bytes_or_String] | None = (),
    ignore_hidden: bool = False,
    logger: Logger | None = None,
) -> Generator[tuple[bytes, list[bytes], list[bytes]]]: ...

class MoveOperation(Enum):
    MOVE = 0
    COPY = 1
    LINK = 2
    HARDLINK = 3
    REFLINK = 4
    REFLINK_AUTO = 5

class FilesystemError(Exception):
    paths: Sequence[bytes]

    def __init__(
        self,
        reason: str,
        verb: str,
        paths: Sequence[bytes],
        tb: str | None = None,
    ) -> None: ...
    def get_message(self) -> str: ...
