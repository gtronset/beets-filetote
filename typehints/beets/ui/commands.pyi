from typing import Optional

from beets.library import Library

def move_items(
    lib: Library,
    dest: Optional[bytes],
    query: str,
    copy: bool,
    album: Optional[str],
    pretend: bool,
    confirm: bool = False,
    export: bool = False,
) -> None: ...
