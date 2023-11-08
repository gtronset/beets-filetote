from typing import Any, Callable, Dict, List

from ..dbcore.db import FormattedMapping

class Template:
    def __init__(self, template: str) -> None:
        self.expr: List[Any]
        self.original: str

    def substitute(
        self,
        values: FormattedMapping,
        functions: Dict[str, Callable[..., str]] = {},
    ) -> str: ...
