from collections.abc import Callable
from typing import Any

class DefaultTemplateFunctions:
    def functions(self) -> dict[str, Callable[..., Any]]: ...
