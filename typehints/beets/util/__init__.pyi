from enum import Enum
from logging import Logger
from typing import (
    Any,
    AnyStr,
    Generator,
    List,
    Optional,
    Pattern,
    Sequence,
    Tuple,
    Union,
)

from typing_extensions import TypeAlias

Bytes_or_String: TypeAlias = Union[str, bytes]

def ancestry(path: bytes) -> List[str]: ...
def displayable_path(
    path: Union[bytes, str, Tuple[Union[bytes, str], ...]],
    separator: str = "; ",
) -> str: ...
def normpath(path: bytes) -> bytes: ...
def sanitize_path(
    path: str,
    replacements: Optional[Sequence[Sequence[Union[Pattern[Any], str]]]] = None,
) -> str: ...
def unique_path(path: bytes) -> bytes: ...
def bytestring_path(path: Bytes_or_String) -> bytes: ...
def py3_path(path: Union[bytes, str]) -> str: ...
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
    root: Optional[Bytes_or_String] = None,
    clutter: Sequence[str] = (".DS_Store", "Thumbs.db"),
) -> None: ...
def sorted_walk(
    path: AnyStr,
    ignore: Optional[Sequence[Bytes_or_String]] = (),
    ignore_hidden: bool = False,
    logger: Optional[Logger] = None,
) -> Generator[Tuple[bytes, List[bytes], List[bytes]], None, None]: ...

class MoveOperation(Enum):
    MOVE = 0
    COPY = 1
    LINK = 2
    HARDLINK = 3
    REFLINK = 4
    REFLINK_AUTO = 5
