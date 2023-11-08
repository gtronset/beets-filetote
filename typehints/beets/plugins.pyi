from logging import Logger
from typing import Any, Callable, Dict, List, Optional, Set

from beets import config

class BeetsPlugin:
    def __init__(self, name: Optional[str] = None):
        """Perform one-time plugin setup."""
        self.name: str = name or self.__module__.split(".")[-1]
        self.config = config[self.name]

        self._log: Logger

    def register_listener(self, event: str, func: Callable[..., Any]) -> None: ...

def send(event: str, **arguments: Any) -> List[Any]: ...
def find_plugins() -> List[Any]: ...
def load_plugins(names: List[str]) -> None: ...

_instances: Dict[Any, Any]

_classes: Set[Any]
