"""Setup for tests for the beets-filetote plugin."""

import functools
import os
import shutil
import sys
import tempfile
import unittest

from pathlib import Path

from beets import config, logging, util
from beets.test._common import DummyIO  # noqa: PLC2701
from beets.util import FilesystemError

# Propagate to root logger so nosetest can capture it
log = logging.getLogger("beets")
log.propagate = True
log.setLevel(logging.DEBUG)

PLATFORM = sys.platform

# OS feature testing functions. These functions utilize `beets.util` functions
# to test if symlinks, hardlinks, and reflinks are supported on the current platform
# and filesystem, instead of just simple OS Platform checks (previously used).
# These results are cached to avoid redundant checks across tests which helps
# performance.


@functools.lru_cache(maxsize=1)
def check_symlink() -> bool:
    """Tests if symlinks are usable using `beets.util.link`."""
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        src = tmpdir / "symlink_src"
        dst = tmpdir / "symlink_dst"

        try:
            # Symlink source does not need to exist, it's just a path/pointer.
            util.link(util.bytestring_path(src), util.bytestring_path(dst))

            return dst.is_symlink()

        except (FilesystemError, OSError) as e:
            # Catch Beets' custom error and any underlying OSError
            log.debug(f"Symlink check failed: {e}")
            return False


@functools.lru_cache(maxsize=1)
def check_hardlink() -> bool:
    """Tests if hardlinks are usable using `beets.util.hardlink`.

    The `beets.util.hardlink` function catches EXDEV errors and raises
    `FilesystemError`.
    """
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        src = tmpdir / "hardlink_src"
        dst = tmpdir / "hardlink_dst"

        try:
            src.write_bytes(b"test")

            util.hardlink(util.bytestring_path(src), util.bytestring_path(dst))

            return dst.exists() and src.stat().st_ino == dst.stat().st_ino

        except (FilesystemError, OSError) as e:
            log.debug(f"Hardlink check failed: {e}")
            return False


@functools.lru_cache(maxsize=1)
def check_reflink() -> bool:
    """Tests if reflinks are usable using `beets.util.reflink`.

    The `beets.util.reflink` function catches EXDEV and EOPNOTSUPP errors and
    raises `FilesystemError`.
    """
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        src = tmpdir / "reflink_src"
        dst = tmpdir / "reflink_dst"

        try:
            src.write_bytes(b"test")

            # Attempt the reflink. `fallback=False` ensures it fails if not supported,
            # instead of silently performing a full copy.
            util.reflink(
                util.bytestring_path(src), util.bytestring_path(dst), fallback=False
            )

            return dst.exists() and src.stat().st_ino != dst.stat().st_ino

        except (FilesystemError, ImportError, OSError) as e:
            # Also catch ImportError in case the `reflink` lib is not installed
            log.debug(f"Reflink check failed: {e}")
            return False


# Run/Test feature probes
HAVE_SYMLINK = check_symlink()
HAVE_HARDLINK = check_hardlink()
HAVE_REFLINK = check_reflink()


# TODO(gtronset): Remove backwards compatibility support for bytes paths in assertions
# once all tests are updated to use Path objects instead of bytestring paths.
# https://github.com/gtronset/beets-filetote/pull/255
class AssertionsMixin:
    """A mixin with additional unit test assertions."""

    assertions = unittest.TestCase()

    def assert_exists(self, path: Path) -> None:
        """Assertion that a file exists."""
        assert path.exists(), f"file does not exist: {path!r}"

    def assert_does_not_exist(self, path: Path) -> None:
        """Assertion that a file does not exists."""
        assert not path.exists(), f"file exists: {path!r}"

    def assert_equal_path(self, path_a: Path, path_b: Path) -> None:
        """Check that two paths are equal."""
        assert path_a.resolve() == path_b.resolve(), (
            f"paths are not equal: {path_a!r} and {path_b!r}"
        )


# A test harness for all beets tests.
# Provides temporary, isolated configuration.
class TestCase(unittest.TestCase):
    """A unittest.TestCase subclass that saves and restores beets'
    global configuration. This allows tests to make temporary
    modifications that will then be automatically removed when the test
    completes. Also provides some additional assertion methods, a
    temporary directory, and a DummyIO.
    """

    def setUp(self) -> None:
        # A "clean" source list including only the defaults.
        config.sources = []
        config.read(user=False, defaults=True)

        # Direct paths to a temporary directory. Tests can also use this
        # temporary directory.
        self.temp_dir = Path(tempfile.mkdtemp())

        config["statefile"] = str(self.temp_dir / "state.pickle")
        config["library"] = str(self.temp_dir / "library.db")
        config["directory"] = str(self.temp_dir / "libdir")

        # Set $HOME, which is used by confit's `config_dir()` to create
        # directories.
        self._old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)

        # Initialize, but don't install, a DummyIO.
        self.in_out = DummyIO()

    def tearDown(self) -> None:
        if self.temp_dir.is_dir():
            shutil.rmtree(self.temp_dir)
        if self._old_home is None:
            del os.environ["HOME"]
        else:
            os.environ["HOME"] = self._old_home
        self.in_out.restore()

        config.clear()
