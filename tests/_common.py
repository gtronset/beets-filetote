"""Setup for tests for the beets-filetote plugin."""

import os
import shutil
import sys
import tempfile
import unittest

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

    TEST = unittest.TestCase()

    def assert_exists(self, path):
        """Assertion that a file exists."""
        self.TEST.assertTrue(
            os.path.exists(util.syspath(path)),
            f"file does not exist: {path!r}",
        )

    def assert_does_not_exist(self, path):
        """Assertion that a file does not exists."""
        self.TEST.assertFalse(
            os.path.exists(util.syspath(path)),
            f"file exists: {path!r}",
        )

    def assert_equal_path(self, path_a, path_b):
        """Check that two paths are equal."""
        self.TEST.assertEqual(
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

    def setUp(self):
        # A "clean" source list including only the defaults.
        config.sources = []
        config.read(user=False, defaults=True)

        # Direct paths to a temporary directory. Tests can also use this
        # temporary directory.
        self.temp_dir = util.bytestring_path(tempfile.mkdtemp())

        config["statefile"] = util.py3_path(
            os.path.join(self.temp_dir, b"state.pickle")
        )
        config["library"] = util.py3_path(os.path.join(self.temp_dir, b"library.db"))
        config["directory"] = util.py3_path(os.path.join(self.temp_dir, b"libdir"))

        # Set $HOME, which is used by confit's `config_dir()` to create
        # directories.
        self._old_home = os.environ.get("HOME")
        os.environ["HOME"] = util.py3_path(self.temp_dir)

        # Initialize, but don't install, a DummyIO.
        self.in_out = DummyIO()

    def tearDown(self):
        # pylint: disable=protected-access,no-member
        # self.lib._close()

        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        if self._old_home is None:
            del os.environ["HOME"]
        else:
            os.environ["HOME"] = self._old_home
        self.in_out.restore()

        config.clear()
        log.debug("===#############===")


# Mock I/O.


class InputException(Exception):
    """Provides handling of input exceptions."""

    def __init__(self, output=None):
        self.output = output

    def __str__(self):
        msg = "Attempt to read with no input provided."
        if self.output is not None:
            msg += f" Output: {self.output!r}"
        return msg


class DummyOut:
    """Provides fake/"dummy" output handling."""

    encoding = "utf-8"

    def __init__(self):
        self.buf = []

    def write(self, buf_item):
        """Writes to buffer"""
        self.buf.append(buf_item)

    def get(self):
        """Get from buffer"""
        return "".join(self.buf)

    def flush(self):
        """Flushes/clears output."""
        self.clear()

    def clear(self):
        """Resets buffer."""
        self.buf = []


class DummyIn:
    """Provides fake/"dummy" input handling."""

    encoding = "utf-8"

    def __init__(self, out=None):
        self.buf = []
        self.reads = 0
        self.out = out

    def add(self, buf_item):
        """Add buffer input"""
        self.buf.append(buf_item + "\n")

    def readline(self):
        """Reads buffer line"""
        if not self.buf:
            if self.out:
                raise InputException(self.out.get())

            raise InputException()
        self.reads += 1
        return self.buf.pop(0)


class DummyIO:
    """Mocks input and output streams for testing UI code."""

    def __init__(self):
        self.stdout = DummyOut()
        self.stdin = DummyIn(self.stdout)

    def addinput(self, inputs):
        """Adds IO input."""
        self.stdin.add(inputs)

    def getoutput(self):
        """Gets IO output."""
        res = self.stdout.get()
        self.stdout.clear()
        return res

    def readcount(self):
        """Reads from stdin"""
        return self.stdin.reads

    def install(self):
        """Setup stdin and stdout"""
        sys.stdin = self.stdin
        sys.stdout = self.stdout

    def restore(self):
        """Restores/reset both stdin and stdout"""
        sys.stdin = sys.__stdin__
        sys.stdout = sys.__stdout__
