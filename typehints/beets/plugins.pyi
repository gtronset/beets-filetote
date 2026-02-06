from collections.abc import Callable
from logging import Logger
from typing import Any

from beets import config

class BeetsPlugin:
    name: str
    config = config
    _log: Logger
    def __init__(self, name: str | None = None): ...
    def register_listener(self, event: str, func: Callable[..., Any]) -> None: ...

def send(event: str, **arguments: Any) -> list[Any]: ...
def find_plugins() -> list[Any]: ...
def load_plugins(names: list[str] = ...) -> None: ...

_instances: list[BeetsPlugin]

_classes: set[Any]
