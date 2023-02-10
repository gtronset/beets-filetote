"""Tests "pattern" functionality for the beets-filetote plugin."""

import logging

from beets import config

from tests.helper import FiletoteTestCase, capture_log

log = logging.getLogger("beets")


class FiletotePatternTest(FiletoteTestCase):
    """
    Tests to check that Filetote grabs artfacts by user-definited patterns.
    """

    def setUp(self, audible_plugin: bool = False) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_patterns_match(self) -> None:
        """Tests that renaming works when copying."""
        config["filetote"]["print_ignored"] = True
        config["filetote"]["extensions"] = ""
        config["filetote"]["patterns"] = {
            "file-pattern": ["[Aa]rtifact.file", "artifact[23].file"],
            "nfo-pattern": ["*.nfo"],
        }

        with capture_log() as logs:
            self._run_importer()

        for line in logs:
            if line.startswith("filetote:"):
                log.info(line)

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        # self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        # self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
