from typing_extensions import TypeAlias

Bytes_or_String: TypeAlias = int | str

def supported_at(path: Bytes_or_String) -> bool: ...
