from collections.abc import Callable
from typing import Any


class DefaultTemplateFunctions:
    def __init__(self, item: Any | None = ..., lib: Any | None = ...) -> None: ...

    def functions(self) -> dict[str, Callable[..., Any]]: ...
