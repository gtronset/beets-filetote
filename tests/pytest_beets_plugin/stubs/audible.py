"""Minimal stub of the beets-audible plugin used in integration tests."""

from typing import Any

from beets.plugins import BeetsPlugin


class Audible(BeetsPlugin):
    """Minimal stub of the beets-audible plugin used in integration tests."""

    name = "audible"

    def __init__(self) -> None:
        """Initialize the Audible plugin stub."""
        super().__init__()
        self.early_import_stages: list[Any] = []
