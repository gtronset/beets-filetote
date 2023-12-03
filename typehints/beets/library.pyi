from collections.abc import Callable
from typing import Any

from .dbcore import Database
from .dbcore.db import Model

class DefaultTemplateFunctions:
    def functions(self) -> dict[str, Callable[..., Any]]: ...

class Library(Database):
    path: bytes
    directory: bytes
    path_formats: list[tuple[str, str]]
    replacements: list[str] | None
    def __init__(
        self,
        path: bytes,
        directory: str = "~/Music",
        path_formats: list[tuple[str, str]] = [],
        replacements: list[str] | None = None,
    ): ...

class LibModel(Model): ...

class Item(LibModel):
    path: bytes

    def __init__(self) -> None: ...
