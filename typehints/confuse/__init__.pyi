from typing import Any, List, Optional

class ConfigView(object):
    def __getitem__(self, key: str) -> Any: ...
    def __setitem__(self, key: str, value: Any) -> Any: ...

class RootView(ConfigView):
    def __init__(self, sources: List[Any]):
        self.sources: List[Any] = list(sources)

class Configuration(RootView):
    def __init__(
        self,
        appname: str,
        modname: Optional[str] = None,
        read: bool = True,
    ):
        super(Configuration, self).__init__([])

class LazyConfig(Configuration):
    def __init__(self, appname: str, modname: Optional[str] = None):
        super(LazyConfig, self).__init__(appname, modname, False)

    def clear(self) -> None: ...
