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
def modify_items(
    lib: Library,
    mods: dict[str, str],
    dels: dict[str, str],
    query: str,
    write: bool = True,
    move: bool = True,
    album: str | None = None,
    confirm: bool = False,
) -> None: ...
def update_items(
    lib: Library,
    query: str,
    album: str | None = None,
    move: bool = True,
    pretend: bool = True,
    fields: list[str] | None = None,
    exclude_fields: list[str] | None = None,
) -> None: ...
