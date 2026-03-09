"""Logging helpers for beets plugin tests."""

from __future__ import annotations

import contextlib
import logging
import re

from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from beets import config

if TYPE_CHECKING:
    from collections.abc import Generator

LogLevels: TypeAlias = Literal[
    10,  # logging.DEBUG
    20,  # logging.INFO
    30,  # logging.WARNING
    40,  # logging.ERROR
    50,  # logging.CRITICAL
]


# Matches str.format()-style placeholders: {}, {0}, {name}, {!r}, {0!r}, etc.
_STR_FORMAT_RE = re.compile(r"\{[^}]*\}")

_beets_log_fix_installed = False


def install_beets_log_fix() -> None:
    """Monkey-patch beets logger to handle ``str.format``-style strings.

    Beets uses ``log.debug("Sending event: {}", event)`` and
    ``log.debug("Parsed query: {!r}", query)`` which are
    ``str.format`` style, but Python's :mod:`logging` expects printf
    style (``%s``).  This causes :class:`TypeError` when a DEBUG-level
    handler is attached (e.g. by pytest's ``log_level = "DEBUG"``).

    Call once at session startup (e.g. from ``conftest.py``).
    """
    global _beets_log_fix_installed  # noqa: PLW0603
    if _beets_log_fix_installed:
        return
    _beets_log_fix_installed = True

    original_log = logging.Logger._log  # noqa: SLF001

    def _patched_log(
        self: logging.Logger,
        level: int,
        msg: object,
        args: object,
        **kwargs: object,
    ) -> None:
        if args and isinstance(msg, str) and _STR_FORMAT_RE.search(msg):
            try:
                msg = msg.format(*args) if isinstance(args, tuple) else msg.format(args)
                args = None
            except (IndexError, KeyError, ValueError):
                pass
        original_log(self, level, msg, args, **kwargs)  # type: ignore[arg-type]

    logging.Logger._log = _patched_log  # type: ignore[assignment]  # noqa: SLF001


# Auto-apply the fix when this module is imported.
install_beets_log_fix()


class ListLogHandler(logging.Handler):
    """A logging handler that records messages in a list, including tracebacks."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the handler and its message list."""
        super().__init__(*args, **kwargs)
        self.messages: list[str] = []
        self.setFormatter(logging.Formatter("%(message)s\n%(exc_text)s"))

    def emit(self, record: logging.LogRecord) -> None:
        """Appends the formatted log record to the message list."""
        msg = self.format(record)
        if msg.endswith("\nNone"):
            msg = msg.removesuffix("\nNone")
        self.messages.append(msg)


@contextlib.contextmanager
def capture_beets_log(
    logger_name: str = "beets",
    level: LogLevels = logging.DEBUG,
) -> Generator[list[str], None, None]:
    """Context manager that captures log output from a beets logger.

    Usage::

        with capture_beets_log("beets.filetote") as logs:
            do_something()
        assert any("expected message" in line for line in logs)
    """
    logger = logging.getLogger(logger_name)

    original_logger_level = logger.level
    original_verbose = config["verbose"].get()

    if level <= logging.DEBUG:
        required_verbosity = 2
    elif level <= logging.INFO:
        required_verbosity = 1
    else:
        required_verbosity = 0

    config["verbose"] = required_verbosity
    logger.setLevel(level)

    handler = ListLogHandler()
    logger.addHandler(handler)

    try:
        yield handler.messages
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_logger_level)
        config["verbose"] = original_verbose


# Backward-compatible alias
capture_log_with_traceback = capture_beets_log
