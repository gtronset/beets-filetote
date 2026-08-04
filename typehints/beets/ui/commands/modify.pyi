from dataclasses import dataclass

from beets.library import Library

@dataclass
class ModifyOperation:
    operator: str | None
    value: str

def modify_items(
    lib: Library,
    mods: dict[str, ModifyOperation],
    dels: dict[str, ModifyOperation],
    query: str,
    write: bool = True,
    move: bool = True,
    album: str | None = None,
    confirm: bool = False,
    inherit: bool = True,
) -> None: ...
