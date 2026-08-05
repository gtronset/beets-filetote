from collections.abc import Callable

from beets.library import LibModel, Library

class DefaultTemplateFunctions:
    def __init__(self, item: LibModel, lib: Library | None) -> None: ...
    def functions(self) -> dict[str, Callable[..., str]]: ...
