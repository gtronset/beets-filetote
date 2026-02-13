"""Tests that renaming using `item_fields` work as expected, when the
`inline` plugin is loaded.
"""

import logging

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteInlineRenameTest(FiletoteTestCase):
    """Tests that renaming using `item_fields` work as expected, when the
    `inline` plugin is loaded.
    """

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Provides shared setup for tests."""
        super().setUp(other_plugins=["inline"])

    def test_rename_works_with_inline_plugin(self) -> None:
        """Ensure that Filetote can rename fields as expected with the `inline`
        plugin is enabled.
        """
        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".*"
        config["filetote"]["patterns"] = {
            "file-pattern": ["*.file"],
        }
        config["paths"]["ext:file"] = (
            "$albumpath/%if{$multidisc,Disc $disc} - $old_filename"
        )

        config["item_fields"]["multidisc"] = "1 if disctotal > 1 else 0"

        self.lib.path_formats[0] = (
            "default",
            self.fmt_path("$artist", "$album", "%if{$multidisc,Disc $disc/}$title"),
        )

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/Disc 01/Disc 01 - artifact.file")
