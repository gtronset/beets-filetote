"""Simplified stand-in for the upstream convert plugin used in tests."""

from __future__ import annotations

import os
import shutil

from contextlib import suppress
from typing import TYPE_CHECKING, Any, Callable, cast

from beets import config, util
from beets.plugins import BeetsPlugin

if TYPE_CHECKING:
    from beets.importer import ImportSession, ImportTask
    from beets.library import Library


class ConvertPlugin(BeetsPlugin):
    """Minimal convert plugin implementation for the test environment."""

    def __init__(self) -> None:
        """Initialize the stub convert plugin used in tests."""
        super().__init__()
        self.early_import_stages: list[Callable[[ImportSession, ImportTask], None]] = [
            self._capture_import_stage
        ]
        self._pending: list[tuple[int, bytes]] = []
        self.register_listener("cli_exit", self._finalize_conversions)

    def _capture_import_stage(self, _session: ImportSession, task: ImportTask) -> None:
        """Record items that should be converted later."""
        convert_config = config["convert"]
        if not convert_config.exists():
            return

        self._pending = [
            (item.id, util.bytestring_path(item.path)) for item in task.imported_items()
        ]

    def _finalize_conversions(self, lib: Library) -> None:
        """Copy files with a new extension and update library metadata."""
        if not self._pending:
            return

        convert_config = config["convert"]
        settings: dict[str, object] = convert_config.get(dict) or {}

        target_ext = str(settings.get("format", "flac")).lstrip(".")
        dest_override = settings.get("dest")
        dest_root_input = cast("str | bytes", dest_override or lib.directory)
        dest_root = util.bytestring_path(dest_root_input)
        remove_original = bool(settings.get("delete_originals"))

        target_suffix = b"." + target_ext.encode("utf-8")

        library = cast("Any", lib)

        for item_id, source_path in self._pending:
            item = library.get_item(item_id)
            if not item:
                continue

            base_destination = item.destination()
            destination_name = os.path.basename(base_destination)
            destination_stem = os.path.splitext(destination_name)[0]

            dest_dir = dest_root if dest_override else os.path.dirname(base_destination)

            dest_path = os.path.join(dest_dir, destination_stem + target_suffix)

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copyfile(source_path, dest_path)

            if remove_original and os.path.exists(source_path):
                with suppress(OSError):
                    os.remove(source_path)

            item.path = dest_path
            item.format = target_ext.upper()
            item.store()

        self._pending = []
