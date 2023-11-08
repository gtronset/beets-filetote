from typing import Any, Callable, Dict, List, Optional, Tuple

from .dbcore import Database
from .dbcore.db import Model

class DefaultTemplateFunctions:
    def functions(self) -> Dict[str, Callable[..., Any]]: ...

class Library(Database):
    def __init__(
        self,
        path: bytes,
        directory: str = "~/Music",
        path_formats: List[Tuple[str, str]] = [
            ("default", "$artist/$album/$track $title")
        ],
        replacements: Optional[List[str]] = None,
    ):
        self.directory: bytes
        self.path_formats: List[Tuple[str, str]] = path_formats
        self.replacements: Optional[List[str]] = replacements

class LibModel(Model):
    pass

class Item(LibModel):
    def __init__(self) -> None:
        self.path: bytes
