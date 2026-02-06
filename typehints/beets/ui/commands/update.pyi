from beets.library import Library

def update_items(
    lib: Library,
    query: str,
    album: str | None = None,
    move: bool = True,
    pretend: bool = True,
    fields: list[str] | None = None,
    exclude_fields: list[str] | None = None,
) -> None: ...
