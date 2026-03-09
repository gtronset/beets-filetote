"""Vendored test infrastructure for beets plugin tests.

Contains DummyIO and OS feature probes, decoupled from upstream beets
test internals.
"""

import functools
import sys
import tempfile

from pathlib import Path
from typing import TYPE_CHECKING

from beets import logging, util
from beets.util import FilesystemError

if TYPE_CHECKING:
    from typing import TextIO

log = logging.getLogger("beets")
log.propagate = True
log.setLevel(logging.DEBUG)

PLATFORM = sys.platform


# ---------------------------------------------------------------------------
# OS feature probes
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def check_symlink() -> bool:
    """Tests if symlinks are usable using ``beets.util.link``."""
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        src = tmpdir / "symlink_src"
        dst = tmpdir / "symlink_dst"

        try:
            util.link(util.bytestring_path(src), util.bytestring_path(dst))
            return dst.is_symlink()
        except (FilesystemError, OSError) as e:
            log.debug(f"Symlink check failed: {e}")
            return False


@functools.lru_cache(maxsize=1)
def check_hardlink() -> bool:
    """Tests if hardlinks are usable using ``beets.util.hardlink``."""
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        src = tmpdir / "hardlink_src"
        dst = tmpdir / "hardlink_dst"

        try:
            src.touch()
            util.hardlink(util.bytestring_path(src), util.bytestring_path(dst))
            return dst.exists() and src.stat().st_ino == dst.stat().st_ino
        except (FilesystemError, OSError) as e:
            log.debug(f"Hardlink check failed: {e}")
            return False


@functools.lru_cache(maxsize=1)
def check_reflink() -> bool:
    """Tests if reflinks are usable using ``beets.util.reflink``."""
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        src = tmpdir / "reflink_src"
        dst = tmpdir / "reflink_dst"

        try:
            src.write_bytes(b"test")
            util.reflink(
                util.bytestring_path(src),
                util.bytestring_path(dst),
                fallback=False,
            )
            return dst.exists() and src.stat().st_ino != dst.stat().st_ino
        except (FilesystemError, OSError) as e:
            log.debug(f"Reflink check failed: {e}")
            return False


HAVE_SYMLINK = check_symlink()
HAVE_HARDLINK = check_hardlink()
HAVE_REFLINK = check_reflink()


# ---------------------------------------------------------------------------
# Vendored DummyIO
# ---------------------------------------------------------------------------


class InputError(Exception):
    def __init__(self, output: str | None = None):
        self.output = output

    def __str__(self) -> str:
        msg = "Attempt to read with no input provided."
        if self.output is not None:
            msg += f" Output: {self.output!r}"
        return msg


class DummyOut:
    encoding = "utf-8"

    def __init__(self) -> None:
        self.buf: list[str] = []

    def write(self, s: str | bytes) -> None:
        if isinstance(s, bytes):
            s = s.decode(self.encoding, "replace")
        self.buf.append(s)

    def get(self) -> str:
        return "".join(self.buf)

    def flush(self) -> None:
        pass

    def clear(self) -> None:
        self.buf = []


class DummyIn:
    encoding = "utf-8"

    def __init__(self, out: DummyOut | None = None):
        self.buf: list[str] = []
        self.reads: int = 0
        self.out = out

    def add(self, s: str) -> None:
        self.buf.append(f"{s}\n")

    def close(self) -> None:
        pass

    def readline(self) -> str:
        if not self.buf:
            if self.out:
                raise InputError(self.out.get())
            else:
                raise InputError()
        self.reads += 1
        return self.buf.pop(0)


class DummyIO:
    """Mocks input and output streams for testing UI code."""

    def __init__(self) -> None:
        self.stdout: DummyOut = DummyOut()
        self.stdin: DummyIn = DummyIn(self.stdout)
        self._orig_stdin: TextIO | None = None
        self._orig_stdout: TextIO | None = None

    def addinput(self, s: str) -> None:
        self.stdin.add(s)

    def getoutput(self) -> str:
        res = self.stdout.get()
        self.stdout.clear()
        return res

    def readcount(self) -> int:
        return self.stdin.reads

    def install(self) -> None:
        self._orig_stdin = sys.stdin
        self._orig_stdout = sys.stdout
        sys.stdin = self.stdin
        sys.stdout = self.stdout

    def restore(self) -> None:
        if self._orig_stdin is not None:
            sys.stdin = self._orig_stdin
        if self._orig_stdout is not None:
            sys.stdout = self._orig_stdout
