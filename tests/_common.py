"""Setup for tests for the beets-filetote plugin."""

import os
import shutil
import sys
import tempfile
import unittest
from typing import List, Optional

import reflink
from beets import config, logging, util

# Test resources path.
RSRC = util.bytestring_path(os.path.join(os.path.dirname(__file__), "rsrc"))

# Propagate to root logger so nosetest can capture it
log = logging.getLogger("beets")
log.propagate = True
log.setLevel(logging.DEBUG)

PLATFORM = sys.platform

# OS feature test.
HAVE_SYMLINK = PLATFORM != "win32"
HAVE_HARDLINK = PLATFORM != "win32"
HAVE_REFLINK = reflink.supported_at(tempfile.gettempdir())


class AssertionsMixin:
    """A mixin with additional unit test assertions."""

    assertions = unittest.TestCase()

    def assert_exists(self, path: bytes) -> None:
        """Assertion that a file exists."""
        self.assertions.assertTrue(
            os.path.exists(util.syspath(path)),
            f"file does not exist: {path!r}",
        )

    def assert_does_not_exist(self, path: bytes) -> None:
        """Assertion that a file does not exists."""
        self.assertions.assertFalse(
            os.path.exists(util.syspath(path)),
            f"file exists: {path!r}",
        )

    def assert_equal_path(self, path_a: bytes, path_b: bytes) -> None:
        """Check that two paths are equal."""
        self.assertions.assertEqual(
            util.normpath(path_a),
            util.normpath(path_b),
            f"paths are not equal: {path_a!r} and {path_b!r}",
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

        config["statefile"] = os.fsdecode(
            os.path.join(self.temp_dir, b"state.pickle")
        )
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


# Mock I/O.


class InputException(Exception):
    """Provides handling of input exceptions."""

    def __init__(self, output: Optional[str] = None) -> None:
        self.output = output

    def __str__(self) -> str:
        msg = "Attempt to read with no input provided."
        if self.output is not None:
            msg += f" Output: {self.output!r}"
        return msg


class DummyOut:
    """Provides fake/"dummy" output handling."""

    encoding = "utf-8"

    def __init__(self) -> None:
        self.buf: List[str] = []

    def write(self, buf_item: str) -> None:
        """Writes to buffer"""
        self.buf.append(buf_item)

    def get(self) -> str:
        """Get from buffer"""
        return "".join(self.buf)

    def flush(self) -> None:
        """Flushes/clears output."""
        self.clear()

    def clear(self) -> None:
        """Resets buffer."""
        self.buf = []


class DummyIn:
    """Provides fake/"dummy" input handling."""

    encoding = "utf-8"

    def __init__(self, out: Optional[DummyOut] = None) -> None:
        self.buf: List[str] = []
        self.reads: int = 0
        self.out: Optional[DummyOut] = out

    def add(self, buf_item: str) -> None:
        """Add buffer input"""
        self.buf.append(buf_item + "\n")

    def readline(self) -> str:
        """Reads buffer line"""
        if not self.buf:
            if self.out:
                raise InputException(self.out.get())

            raise InputException()
        self.reads += 1
        return self.buf.pop(0)


class DummyIO:
    """Mocks input and output streams for testing UI code."""

    def __init__(self) -> None:
        self.stdout: DummyOut = DummyOut()
        self.stdin: DummyIn = DummyIn(self.stdout)

    def addinput(self, inputs: str) -> None:
        """Adds IO input."""
        self.stdin.add(inputs)

    def getoutput(self) -> str:
        """Gets IO output."""
        res = self.stdout.get()
        self.stdout.clear()
        return res

    def readcount(self) -> int:
        """Reads from stdin"""
        return self.stdin.reads

    def install(self) -> None:
        """Setup stdin and stdout"""
        sys.stdin = self.stdin  # type: ignore[assignment]
        sys.stdout = self.stdout  # type: ignore[assignment]

    def restore(self) -> None:
        """Restores/reset both stdin and stdout"""
        sys.stdin = sys.__stdin__
        sys.stdout = sys.__stdout__
