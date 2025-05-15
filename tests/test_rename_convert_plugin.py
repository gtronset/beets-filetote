"""Tests that renaming using `item_fields` work as expected, when the
`inline` plugin is loaded.
"""

import logging
import os

from typing import List, Optional

from beets import config

from tests.helper import FiletoteTestCase, MediaSetup

log = logging.getLogger("beets")


class FiletoteConvertRenameTest(FiletoteTestCase):
    """Tests that renaming using `item_fields` work as expected, when the
    `convert` plugin is loaded.
    """

    def setUp(self, _other_plugins: Optional[List[str]] = None) -> None:
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

        temp_convert_dir = os.path.join(self.temp_dir, b"temp_convert_dir")
        os.makedirs(temp_convert_dir)

        config["convert"] = {
            "auto": True,
            "dest": os.path.join(self.lib_dir, b"Tag Artist", b"Tag Album"),
            "copy_album_art": True,
            "delete_originals": False,
            "format": "flac",
            "never_convert_lossy_files": False,
            "tmpdir": temp_convert_dir,
            "quiet": False,
        }

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 1.flac")
