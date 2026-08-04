import re

MULTIDISC_MARKERS: tuple[bytes, ...]
MULTIDISC_PAT_FMT: bytes
MULTIDISC_PATTERNS: list[re.Pattern[str] | re.Pattern[bytes]]
