"""Setup for tests for the beets-filetote plugin."""

import functools
import os
import shutil
import sys
import tempfile
import unittest

from beets import config, logging, util
from beets.test._common import DummyIO  # noqa: PLC2701
from beets.util import FilesystemError

# Test resources path.
RSRC = util.bytestring_path(os.path.join(os.path.dirname(__file__), "rsrc"))

# Propagate to root logger so nosetest can capture it
log = logging.getLogger("beets")
log.propagate = True
log.setLevel(logging.DEBUG)

PLATFORM = sys.platform

# OS feature testing functions. These functions utilize beets.util functions
# to robustly test if symlinks, hardlinks, and reflinks are supported on
# the current platform and filesystem, instead of simple OS Platform checks.


@functools.lru_cache(maxsize=1)
def check_symlink() -> bool:
    """Robustly tests if symlinks are usable using beets.util.link."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_bytes = util.bytestring_path(os.path.join(tmpdir, "symlink_src"))
        dst_bytes = util.bytestring_path(os.path.join(tmpdir, "symlink_dst"))

        try:
            # Symlink source does not need to exist, it's just a path/pointer.
            util.link(src_bytes, dst_bytes)

            return os.path.islink(dst_bytes)

        except (FilesystemError, OSError) as e:
            # Catch Beets' custom error and any underlying OSError
            log.debug(f"Symlink check failed: {e}")
            return False


@functools.lru_cache(maxsize=1)
def check_hardlink() -> bool:
    """Robustly tests if hardlinks are usable using beets.util.hardlink.

    The beets.util.hardlink function catches EXDEV errors and raises FilesystemError.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        src_bytes = util.bytestring_path(os.path.join(tmpdir, "hardlink_src"))
        dst_bytes = util.bytestring_path(os.path.join(tmpdir, "hardlink_dst"))

        try:
            with open(src_bytes, "wb") as f:
                f.write(b"test")

            util.hardlink(src_bytes, dst_bytes)

            return os.path.exists(dst_bytes) and os.path.samefile(src_bytes, dst_bytes)

        except (FilesystemError, OSError) as e:
            log.debug(f"Hardlink check failed: {e}")
            return False


@functools.lru_cache(maxsize=1)
def check_reflink() -> bool:
    """Robustly tests if reflinks are usable using beets.util.reflink.

    The beets.util.reflink function catches EXDEV and EOPNOTSUPP errors and
    raises FilesystemError.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        src_bytes = util.bytestring_path(os.path.join(tmpdir, "reflink_src"))
        dst_bytes = util.bytestring_path(os.path.join(tmpdir, "reflink_dst"))

        try:
            with open(src_bytes, "wb") as f:
                f.write(b"test")

            # Attempt the reflink. `fallback=False` ensures it fails if not supported,
            # instead of silently performing a full copy.
            util.reflink(src_bytes, dst_bytes, fallback=False)

            return os.path.exists(dst_bytes) and not os.path.samefile(
                src_bytes, dst_bytes
            )

        except (FilesystemError, ImportError, OSError) as e:
            # Also catch ImportError in case the `reflink` lib is not installed
            log.debug(f"Reflink check failed: {e}")
            return False


# Run/Test feature probes
HAVE_SYMLINK = check_symlink()
HAVE_HARDLINK = check_hardlink()
HAVE_REFLINK = check_reflink()


class AssertionsMixin:
    """A mixin with additional unit test assertions."""

    assertions = unittest.TestCase()

    def assert_exists(self, path: bytes) -> None:
        """Assertion that a file exists."""
        assert os.path.exists(util.syspath(path)), f"file does not exist: {path!r}"

    def assert_does_not_exist(self, path: bytes) -> None:
        """Assertion that a file does not exists."""
        assert not os.path.exists(util.syspath(path)), f"file exists: {path!r}"

    def assert_equal_path(self, path_a: bytes, path_b: bytes) -> None:
        """Check that two paths are equal."""
        assert util.normpath(path_a) == util.normpath(path_b), (
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
        self.temp_dir = util.bytestring_path(tempfile.mkdtemp())

        config["statefile"] = os.fsdecode(os.path.join(self.temp_dir, b"state.pickle"))
        config["library"] = os.fsdecode(os.path.join(self.temp_dir, b"library.db"))
        config["directory"] = os.fsdecode(os.path.join(self.temp_dir, b"libdir"))

        # Set $HOME, which is used by confit's `config_dir()` to create
        # directories.
        self._old_home = os.environ.get("HOME")
        os.environ["HOME"] = os.fsdecode(self.temp_dir)

        # Initialize, but don't install, a DummyIO.
        self.in_out = DummyIO()

    def tearDown(self) -> None:
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self._old_home is None:
            del os.environ["HOME"]
        else:
            os.environ["HOME"] = self._old_home
        self.in_out.restore()

        config.clear()
