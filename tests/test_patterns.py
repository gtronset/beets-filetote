"""Tests "pattern" functionality for the beets-filetote plugin."""

import logging
import os

from beets import config

from tests import _common
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
        """Tests that patterns are used to itentify artifacts."""
        config["filetote"]["patterns"] = {
            "file-pattern": ["[aA]rtifact.file", "artifact[23].file"],
            "nfo-pattern": ["*.nfo"],
        }

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")

    def test_patterns_subfolders_match(self) -> None:
        """Tests that patterns are used to itentify artifacts."""

        artwork_dir = os.path.join(self.import_dir, b"the_album", b"artwork")
        os.makedirs(artwork_dir)

        self.create_file(
            path=artwork_dir,
            filename=b"cover.jpg",
        )

        config["filetote"]["patterns"] = {
            "file-pattern": ["/[aA]rtifact.file", "artifact[23].file"],
            "subfolder-pattern": ["/[aA]rtwork/cover.jpg"],
        }

        config["paths"][
            "pattern:subfolder-pattern"
        ] = "$albumpath/artwork/$old_filename"

        if _common.PLATFORM == "win32":
            config["paths"][
                "pattern:subfolder-pattern"
            ] = "$albumpath\\artwork\\$old_filename"

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artwork", b"cover.jpg")

    def test_patterns_path_renaming(self) -> None:
        """Tests that the path definition for `pattern:` prefix works."""
        config["filetote"]["patterns"] = {
            "file-pattern": ["[Aa]rtifact.file", "artifact[23].file"],
            "nfo-pattern": ["*.nfo"],
        }
        config["paths"][
            "pattern:file-pattern"
        ] = "$albumpath/file-pattern $old_filename"

        config["paths"]["pattern:nfo-pattern"] = "$albumpath/nfo-pattern $old_filename"

        with capture_log() as logs:
            self._run_importer()

        for line in logs:
            if line.startswith("filetote:"):
                log.info(line)

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"file-pattern artifact.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"file-pattern artifact2.file"
        )
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"nfo-pattern artifact.nfo")
