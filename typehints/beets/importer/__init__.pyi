from logging import Logger

from beets.library import Item, Library

from .tasks import MULTIDISC_MARKERS, MULTIDISC_PAT_FMT

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

# TODO(gtronset): Remove export once Beets v2.3 is no longer supported:
# https://github.com/gtronset/beets-filetote/pull/249
__all__ = ["MULTIDISC_MARKERS", "MULTIDISC_PAT_FMT"]
