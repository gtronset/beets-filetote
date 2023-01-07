"""Tests that music files are ignored for the beets-filetote plugin."""

import logging

from beets import config

from tests.helper import FiletoteTestCase

# import os


log = logging.getLogger("beets")


class FiletoteMusicFilesIgnoredTest(FiletoteTestCase):
    """
    Tests to check that Filetote only copies or moves artifact files and not
    music files
    """

    def setUp(self):
        """Provides shared setup for tests."""
        super().setUp()

        self._base_file_count = None

    def test_only_copies_files_matching_configured_extension(self):
        """First test."""
        self._create_flat_import_dir(media_files=2, generate_pair=False)
        self._setup_import_session(autotag=False)

        self._base_file_count = self._media_count + self._pairs_count

        config["filetote"]["extensions"] = ".file"


# def test_exact_matching_configured_extension(self):
#     config["filetote"]["extensions"] = ".file"

#     self._create_file(
#         os.path.join(self.import_dir, b"the_album"), b"artifact.file2"
#     )

#     self._run_importer()

#     self.assert_number_of_files_in_dir(
#         self._media_count + 2, self.lib_dir, b"Tag Artist", b"Tag Album"
#     )

#     self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
#     self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

#     self.assert_in_import_dir(b"the_album", b"artifact.file2")
#     self.assert_not_in_lib_dir(
#         b"Tag Artist", b"Tag Album", b"artifact.file2"
#     )

# def test_exclude_artifacts_matching_configured_exclude(self):
#     config["filetote"]["extensions"] = ".file"
#     config["filetote"]["exclude"] = "artifact2.file"

#     self._run_importer()

#     self.assert_number_of_files_in_dir(
#         self._media_count + 1, self.lib_dir, b"Tag Artist", b"Tag Album"
#     )

#     self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

#     self.assert_not_in_lib_dir(
#         b"Tag Artist", b"Tag Album", b"artifact2.file"
#     )
#     self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
#     self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

# def test_only_copy_artifacts_matching_configured_filename(self):
#     config["filetote"]["extensions"] = ""
#     config["filetote"]["filenames"] = "artifact.file"

#     self._run_importer()

#     self.assert_number_of_files_in_dir(
#         self._media_count + 1, self.lib_dir, b"Tag Artist", b"Tag Album"
#     )

#     self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

#     self.assert_not_in_lib_dir(
#         b"Tag Artist", b"Tag Album", b"artifact2.file"
#     )
#     self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
#     self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
