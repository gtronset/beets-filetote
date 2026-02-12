"""Tests that renaming using `item_fields` work as expected, when the
`inline` plugin is loaded.
"""

import logging

from typing import TYPE_CHECKING

from beets import config

from tests.helper import FiletoteTestCase, MediaSetup

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger("beets")


class FiletoteConvertRenameTest(FiletoteTestCase):
    """Tests that renaming using `item_fields` work as expected, when the
    `convert` plugin is loaded.
    """

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Provides shared setup for tests."""
        super().setUp(other_plugins=["convert"])

    def test_rename_works_with_inline_plugin(self) -> None:
        """Ensure that Filetote can find artifacts as expected with the `convert`
        plugin is enabled.
        """
        media_file_list = [
            MediaSetup(file_type="wav", count=1),
        ]

        self._create_flat_import_dir(media_files=media_file_list)
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".*"

        temp_convert_dir: Path = self.temp_dir / "temp_convert_dir"
        temp_convert_dir.mkdir(parents=True, exist_ok=True)

        config["convert"] = {
            "auto": True,
            "dest": str(self.lib_dir / "Tag Artist" / "Tag Album"),
            "copy_album_art": True,
            "delete_originals": False,
            "format": "flac",
            "never_convert_lossy_files": False,
            "tmpdir": str(temp_convert_dir),
            "quiet": False,
        }

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.flac")
