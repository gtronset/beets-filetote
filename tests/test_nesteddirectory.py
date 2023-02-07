"""Tests nested directories for the beets-filetote plugin."""

# pylint: disable=duplicate-code

import logging

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

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

        self._base_file_count = self._media_count + self._pairs_count

    def test_only_copies_files_matching_configured_extension(self) -> None:
        """
        Ensures that nested directories are handled bby beets and the the files
        relocate as expected.
        """
        config["filetote"]["extensions"] = ".file"

        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._media_count + 2, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

        self.assert_in_import_dir(b"the_album", b"artifact.nfo")
        self.assert_in_import_dir(b"the_album", b"artifact.lrc")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
