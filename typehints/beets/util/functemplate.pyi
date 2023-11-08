from collections.abc import Callable
from typing import Any

from ..dbcore.db import FormattedMapping

class Template:
    expr: list[Any]
    original: str
    def __init__(self, template: str) -> None: ...
    def substitute(
        self,
        values: FormattedMapping,
        functions: dict[str, Callable[..., str]] = {},
    ) -> str: ...
