from logging import Logger

from beets.library import Item, Library

class ImportSession:
    lib: Library
    logger: Logger | None
    paths: list[bytes]
    query: str | None
    def __init__(
        self,
        lib: Library,
        loghandler: Logger | None,
        paths: list[bytes],
        query: str | None,
    ): ...
    def run(self) -> None: ...

class ImportTask:
    def imported_items(self) -> list[Item]: ...
