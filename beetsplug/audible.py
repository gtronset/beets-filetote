"""Minimal stub of the beets-audible plugin used in integration tests.

The real plugin performs network-dependent initialization via ``tldextract``
which is undesirable in the test environment. This stub provides the minimal
behaviour Filetote cares about: exposing a plugin named ``audible`` so that
Filetote can detect it during ``pluginload`` and treat ``.m4b`` files as
audio files.
"""

from __future__ import annotations

from typing import Callable

from beets.plugins import BeetsPlugin


class Audible(BeetsPlugin):
    """Simple stand-in for the upstream audible plugin."""

    def __init__(self) -> None:
        """Initialize the stub audible plugin used in tests."""
        super().__init__()
        self.config.add({
            "write_description_file": False,
            "write_narrator_file": False,
        })
        self.early_import_stages: list[Callable[..., None]] = []
