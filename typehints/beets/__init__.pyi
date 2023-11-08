from confuse import LazyConfig

class IncludeLazyConfig(LazyConfig):
    def read(self, user: bool = True, defaults: bool = True) -> None: ...

config = IncludeLazyConfig("beets", __name__)
