from re import Pattern

from ..dbcore import Database
from ..dbcore.db import Model
from .models import DefaultTemplateFunctions

class Library(Database):
    path: bytes
    directory: bytes
    path_formats: list[tuple[str, str]]
    replacements: list[tuple[Pattern[str], str]] | None
    def __init__(
        self,
        path: bytes,
        directory: str = "~/Music",
        path_formats: list[tuple[str, str]] = [],
        replacements: list[str] | None = None,
    ): ...

class LibModel(Model): ...

class Item(LibModel):
    id: int
    path: bytes

    def __init__(self) -> None: ...

__all__ = [
    "DefaultTemplateFunctions",
]
