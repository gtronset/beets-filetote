"""Minimal stub of the beets convert plugin used in integration tests."""

from __future__ import annotations

import os

from typing import TYPE_CHECKING, Any

from beets import config
from beets.plugins import BeetsPlugin
from beets.util import bytestring_path

if TYPE_CHECKING:
    from beets.importer import ImportTask


class ConvertPlugin(BeetsPlugin):
    """Minimal stub of the beets convert plugin used in integration tests."""

    name = "convert"

    def __init__(self) -> None:
        """Initialize the ConvertPlugin stub."""
        super().__init__()
        self.register_listener("import_task_files", self._fake_convert)
        self.early_import_stages: list[Any] = []

    def _fake_convert(self, task: ImportTask) -> None:
        # For each imported item, if it's .wav, create a .flac copy in the same
        # directory
        convert_config = config["convert"]
        target_format = convert_config["format"].get(str)
        dest_dir = convert_config["dest"].get(bytes)

        # For each imported item, simulate conversion
        for item in task.imported_items():
            src = item.path
            base, _ = os.path.splitext(os.path.basename(src))
            dest = os.path.join(
                dest_dir, bytestring_path(base) + b"." + target_format.encode()
            )
            # Actually create a dummy converted file
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(b"FAKE " + target_format.encode().upper() + b" DATA")

            # Update item.path to point to the new file (like real Convert)
            item.path = dest
