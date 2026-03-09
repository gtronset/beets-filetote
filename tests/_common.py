"""Backward-compatible shim for beets-filetote tests.

All implementations have moved to ``tests.pytest_beets_plugin``.
This module re-exports them for existing unittest-based tests.
Remove this file once all tests are migrated to native pytest style.
"""

# Re-export everything that existing tests import from here
# Re-export the legacy TestCase for existing unittest-based tests
import os
import shutil
import tempfile
import unittest

from pathlib import Path

from beets import config

from .pytest_beets_plugin._common import (  # noqa: F401
    HAVE_HARDLINK,
    HAVE_REFLINK,
    HAVE_SYMLINK,
    PLATFORM,
    DummyIn,
    DummyIO,
    DummyOut,
    InputError,
    check_hardlink,
    check_reflink,
    check_symlink,
)
from .pytest_beets_plugin.assertions import AssertionsMixin


class TestCase(unittest.TestCase):
    """A unittest.TestCase subclass that saves and restores beets'
    global configuration.

    Deprecated: migrate tests to use the ``beets_plugin_env`` fixture instead.
    """

    def setUp(self) -> None:
        config.sources = []
        config.read(user=False, defaults=True)

        self.temp_dir = Path(tempfile.mkdtemp())

        config["statefile"] = str(self.temp_dir / "state.pickle")
        config["library"] = str(self.temp_dir / "library.db")
        config["directory"] = str(self.temp_dir / "libdir")

        self._old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)

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


__all__ = [
    "HAVE_HARDLINK",
    "HAVE_REFLINK",
    "HAVE_SYMLINK",
    "PLATFORM",
    "AssertionsMixin",
    # "DummyIn",
    # "DummyOut",
    # "InputError",
    # "TestCase",
]
