"""Backward-compatible shim for beets-filetote tests.

All implementations have moved to ``tests.pytest_beets_plugin``.
This module re-exports them for existing unittest-based tests.
Remove this file once all tests are migrated to native pytest style.
"""

from .pytest_beets_plugin import (
    HAVE_HARDLINK,
    HAVE_REFLINK,
    HAVE_SYMLINK,
    PLATFORM,
)
from .pytest_beets_plugin.assertions import AssertionsMixin

__all__ = [
    "HAVE_HARDLINK",
    "HAVE_REFLINK",
    "HAVE_SYMLINK",
    "PLATFORM",
    "AssertionsMixin",
]
