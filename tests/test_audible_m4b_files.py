"""
Tests that m4b music/audiobook files are ignored for the beets-filetote
plugin, when the beets-audible plugin is loaded.
"""

import logging

from typing import List, Optional

from beets import config

from tests.helper import FiletoteTestCase, MediaSetup

log = logging.getLogger("beets")


class FiletoteM4BFilesIgnoredTest(FiletoteTestCase):
    """
    Tests to check that Filetote does not copy music/audiobook files when the
    beets-audible plugin is present.
    """

    def setUp(self, _other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp(other_plugins=["audible", "inline"])

    def test_expanded_music_file_types_are_ignored(self) -> None:
        """Ensure that `.m4b` file types are ignored by Filetote."""

        self._create_flat_import_dir(media_files=[MediaSetup(file_type="m4b", count=1)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".*"

        self._run_cli_command("import")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.m4b")
