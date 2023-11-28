from beets.library import Library

def move_items(
    lib: Library,
    dest: bytes | None,
    query: str,
    copy: bool,
    album: str | None,
    pretend: bool,
    confirm: bool = False,
    export: bool = False,
) -> None: ...
