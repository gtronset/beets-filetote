"""
Tests that renaming using `item_fields` work as expected, when the
`inline` plugin is loaded.
"""

import logging
import os
from typing import List, Optional

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteInlineRenameTest(FiletoteTestCase):
    """
    Tests that renaming using `item_fields` work as expected, when the
    `inline` plugin is loaded.
    """

    def setUp(self, other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp(other_plugins=["inline"])

    def test_rename_works_with_inline_plugin(self) -> None:
        """Ensure that Filetote can rename fields as expected whth the `inline`
        plugin is enabled."""

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".*"
        config["filetote"]["patterns"] = {
            "file-pattern": ["*.file"],
        }
        config["paths"][
            "ext:file"
        ] = "$albumpath/%if{$multidisc,Disc $disc} - $old_filename"

        config["item_fields"]["multidisc"] = "1 if disctotal > 1 else 0"

        self.lib.path_formats[0] = (
            "default",
            os.path.join("$artist", "$album", "%if{$multidisc,Disc $disc/}$title"),
        )

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Disc 01", b"Disc 01 - artifact.file"
        )
