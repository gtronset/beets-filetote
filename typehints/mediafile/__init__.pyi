from typing_extensions import TypeAlias

Bytes_or_String: TypeAlias = str | bytes

class MediaFile:
    def __init__(self, filething: Bytes_or_String, id3v23: bool = False): ...
    def save(self, **kwargs: dict[str, object]) -> None: ...

TYPES: dict[str, str]
