from typing import NamedTuple

from beets.library import Library

class ModifyOperation(NamedTuple):
    operator: str | None
    value: str

def modify_items(
    lib: Library,
    mods: dict[str, str] | dict[str, ModifyOperation],
    dels: list[str],
    query: str,
    write: bool = True,
    move: bool = True,
    album: bool = False,
    confirm: bool = False,
    inherit: bool = True,
) -> None: ...
