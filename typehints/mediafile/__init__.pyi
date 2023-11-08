from typing import Dict, Union

from typing_extensions import TypeAlias

Bytes_or_String: TypeAlias = Union[str, bytes]

class MediaFile(object):
    def __init__(self, filething: Bytes_or_String, id3v23: bool = False): ...
    def save(self, **kwargs: Dict[str, object]) -> None: ...

TYPES: Dict[str, str]
