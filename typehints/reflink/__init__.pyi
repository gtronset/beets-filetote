from typing import Union

from typing_extensions import TypeAlias

Bytes_or_String: TypeAlias = Union[str, bytes]

def supported_at(path: Bytes_or_String) -> bool: ...
