from logging import Logger

from beets import library

class ImportSession:
    lib: library.Library
    logger: Logger | None
    paths: list[bytes]
    query: str | None
    def __init__(
        self,
        lib: library.Library,
        loghandler: Logger | None,
        paths: list[bytes],
        query: str | None,
    ): ...
    def run(self) -> None: ...
