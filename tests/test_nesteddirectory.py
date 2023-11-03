"""Tests nested directories for the beets-filetote plugin."""

# pylint: disable=duplicate-code

import logging
import os

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteFromNestedDirectoryTest(FiletoteTestCase):
    """
    Tests to check that Filetote copies or moves artifact files from a nested directory
    structure. i.e. songs in an album are imported from two directories corresponding to
    disc numbers or flat option is used
    """

    def setUp(self, audible_plugin: bool = False) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_nested_import_dir()
        self._setup_import_session(autotag=False)

        self._base_file_count = self._media_count + self._pairs_count

    def test_copies_file_from_nested_to_library(self) -> None:
        """
        Ensures that nested directories are handled by beets and the the files
        relocate as expected following the default beets behavior (moves to a
        single directory).
        """
        config["filetote"]["extensions"] = ".file"

        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._media_count + 4, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact3.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact4.file")

        self.assert_in_import_dir(b"the_album", b"disc1", b"artifact_disc1.nfo")
        self.assert_in_import_dir(b"the_album", b"disc2", b"artifact_disc2.nfo")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact_disc1.nfo")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact_disc2.lrc")

    def test_copies_file_from_nested_to_nested_library(self) -> None:
        """
        Ensures that nested directory artifacts are relocated as expected
        when beets is set to use a nested library destination.
        """
        config["filetote"]["extensions"] = ".file"
        self.lib.path_formats = [
            ("default", os.path.join("$artist", "$album", "$disc", "$title")),
        ]

        self._run_importer()

        self.assert_number_of_files_in_dir(
            5, self.lib_dir, b"Tag Artist", b"Tag Album", b"01"
        )
        self.assert_number_of_files_in_dir(
            5, self.lib_dir, b"Tag Artist", b"Tag Album", b"02"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"01", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"01", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"02", b"artifact3.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"02", b"artifact4.file")

        self.assert_in_import_dir(b"the_album", b"disc1", b"artifact_disc1.nfo")
        self.assert_in_import_dir(b"the_album", b"disc2", b"artifact_disc2.nfo")

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"01", b"artifact_disc1.nfo"
        )
        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"02", b"artifact_disc2.lrc"
        )
