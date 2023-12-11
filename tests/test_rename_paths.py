"""Tests renaming based on paths for the beets-filetote plugin."""

# pylint: disable=duplicate-code

import logging
from typing import List, Optional

from beets import config

from tests.helper import FiletoteTestCase, capture_log

log = logging.getLogger("beets")


class FiletoteRenamePathsTest(FiletoteTestCase):
    """
    Tests to check that Filetote renames using custom path formats configured
    either in the `paths` scetion of the overall config or in Filetote's.
    """

    def setUp(self, other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_rename_using_filetote_path_when_copying(self) -> None:
        """Tests that renaming works using setting from Filetote's paths."""
        config["filetote"]["extensions"] = ".file .nfo"
        config["filetote"]["paths"] = {
            "ext:file": "$albumpath/$artist - $album",
            "ext:nfo": "$albumpath/$artist - $album",
        }

        self._run_cli_command("import")

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.nfo"
        )

    def test_rename_using_filetote_path_pattern_optional(self) -> None:
        """Tests that renaming patterns works using setting from Filetote's paths
        doesn't require `pattern:` prefix.
        """
        config["filetote"]["patterns"] = {
            "file-pattern": ["[Aa]rtifact.file"],
            "nfo-pattern": ["*.nfo"],
        }
        config["filetote"]["paths"] = {
            "pattern:file-pattern": "$albumpath/file-pattern $old_filename",
            "nfo-pattern": "$albumpath/nfo-pattern $old_filename",
        }

        with capture_log() as logs:
            self._run_cli_command("import")

        for line in logs:
            if line.startswith("filetote:"):
                log.info(line)

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"file-pattern artifact.file"
        )
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"nfo-pattern artifact.nfo")

    def test_rename_prioritizes_filetote_path(self) -> None:
        """Tests that renaming patterns works using setting from Filetote's paths
        doesn't require `pattern:` prefix.
        """
        config["filetote"]["patterns"] = {
            "file-pattern": ["[Aa]rtifact.file"],
            "nfo-pattern": ["*.nfo"],
        }
        config["paths"] = {
            "pattern:file-pattern": "$albumpath/beets_path $old_filename",
            "nfo-pattern": "$albumpath/beets_path $old_filename",
        }
        config["filetote"]["paths"] = {
            "pattern:file-pattern": "$albumpath/filetote_path $old_filename",
            "nfo-pattern": "$albumpath/filetote_path $old_filename",
        }

        with capture_log() as logs:
            self._run_cli_command("import")

        for line in logs:
            if line.startswith("filetote:"):
                log.info(line)

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"filetote_path artifact.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"filetote_path artifact.nfo"
        )
