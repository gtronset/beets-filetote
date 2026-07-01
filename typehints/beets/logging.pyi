from logging import Formatter, Logger

class LegacyFormatter(Formatter): ...

def getLogger(name: str | None = None) -> Logger: ...

DEBUG: int
INFO: int
WARNING: int
ERROR: int
CRITICAL: int
