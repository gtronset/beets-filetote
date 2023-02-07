"""Tests flat directory structure for the beets-filetote plugin."""

# pylint: disable=missing-function-docstring

import logging
import os

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteFromFlatDirectoryTest(FiletoteTestCase):
    """
    Tests to check that Filetote copies or moves artifact files from a
    flat directory (e.g., all songs in an album are imported from a single
    directory). Also tests `extensions` and `filenames` config options.
    """

    def setUp(self, audible_plugin: bool = False) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

        self._base_file_count = self._media_count + self._pairs_count

    def test_only_copies_files_matching_configured_extension(self) -> None:
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

    def test_exact_matching_configured_extension(self) -> None:
        config["filetote"]["extensions"] = ".file"

        self.create_file(os.path.join(self.import_dir, b"the_album"), b"artifact.file2")

        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._media_count + 2, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

        self.assert_in_import_dir(b"the_album", b"artifact.file2")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")

    def test_exclude_artifacts_matching_configured_exclude(self) -> None:
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["exclude"] = "artifact2.file"

        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._media_count + 1, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_only_copy_artifacts_matching_configured_filename(self) -> None:
        config["filetote"]["extensions"] = ""
        config["filetote"]["filenames"] = "artifact.file"

        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._media_count + 1, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_only_copy_artifacts_matching_configured_extension_and_filename(
        self,
    ) -> None:
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["filenames"] = "artifact.nfo"

        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._media_count + 3, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_copy_all_artifacts_by_default(self) -> None:
        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._base_file_count + 4, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_copy_artifacts(self) -> None:
        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._base_file_count + 4, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_ignore_media_files(self) -> None:
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.mp3")

    def test_move_artifacts(self) -> None:
        config["import"]["move"] = True

        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._base_file_count + 4, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact2.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact.nfo")
        self.assert_not_in_import_dir(b"the_album", b"artifact.lrc")

    def test_artifacts_copymove_on_first_media_by_default(self) -> None:
        """By default, all eligible files are grabbed with the first item."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$medianame_old - $old_filename")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1 - artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1 - artifact2.file")
