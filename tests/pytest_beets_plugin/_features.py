"""OS feature probes for beets plugin tests.

Detects availability of symlinks, hardlinks, and reflinks on the current platform.
Results are cached and exposed as module-level constants for use with
`pytest.mark.skipif`.
"""

import functools
import logging
import sys
import tempfile

from pathlib import Path

from beets import util
from beets.util import FilesystemError

log = logging.getLogger("beets")

PLATFORM = sys.platform


@functools.lru_cache(maxsize=1)
def check_symlink() -> bool:
    """Test if symlinks are usable using `beets.util.link`."""
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
    """Test if hardlinks are usable using `beets.util.hardlink`."""
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
    """Test if reflinks are usable using `beets.util.reflink`."""
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


HAVE_SYMLINK: bool = check_symlink()
HAVE_HARDLINK: bool = check_hardlink()
HAVE_REFLINK: bool = check_reflink()
