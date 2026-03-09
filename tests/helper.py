"""Backward-compatible shim for beets-filetote tests.

All implementations have moved to ``tests.pytest_beets_plugin``.
This module re-exports them for existing unittest-based tests.
Remove this file once all tests are migrated to native pytest style.
"""

# Re-export the legacy class for existing unittest-based tests
from .pytest_beets_plugin import (
    FiletoteTestCase,
    MediaSetup,
    capture_log_with_traceback,
)

__all__ = [
    "FiletoteTestCase",
    "MediaSetup",
    "capture_log_with_traceback",
]
