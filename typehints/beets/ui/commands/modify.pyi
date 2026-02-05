from beets.library import Library

def modify_items(
    lib: Library,
    mods: dict[str, str],
    dels: dict[str, str],
    query: str,
    write: bool = True,
    move: bool = True,
    album: str | None = None,
    confirm: bool = False,
    inherit: bool = True,
) -> None: ...
