"""Minimal stub of the beets convert plugin used in integration tests."""

from __future__ import annotations

from pathlib import Path
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

        dest_conf = convert_config["dest"].get(str)
        dest_dir = Path(dest_conf)

        # For each imported item, simulate conversion
        for item in task.imported_items():
            src = item.filepath

            base = src.stem
            dest = dest_dir / f"{base}.{target_format}"

            # Actually create a dummy converted file
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.touch()

            # Update item.path to point to the new file (like real Convert)
            item.path = bytestring_path(dest)
