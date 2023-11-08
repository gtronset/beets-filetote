from logging import Logger
from typing import List, Optional

from beets import library

class ImportSession:
    def __init__(
        self,
        lib: library.Library,
        loghandler: Optional[Logger],
        paths: List[bytes],
        query: Optional[str],
    ):
        self.lib: library.Library
        self.logger: Optional[Logger]
        self.paths: List[bytes]
        self.query: Optional[str]

    def run(self) -> None:
        pass
