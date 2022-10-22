import os
import sys

from beets import config

from tests.helper import CopyFileArtifactsTestCase


class CopyFileArtifactsFromFlatDirectoryTest(CopyFileArtifactsTestCase):
    """
    Tests to check that copyfileartifacts copies or moves artifact files from a flat directory.
    i.e. all songs in an album are imported from a single directory
    Also tests extensions config option
    """

    def setUp(self):
        super(CopyFileArtifactsFromFlatDirectoryTest, self).setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_only_copy_artifacts_matching_configured_extension(self):
        config["copyfileartifacts"]["extensions"] = ".file"

        self._run_importer()

        self.assert_number_of_files_in_dir(
            3, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file2"
        )
        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file3"
        )

    def test_exclude_artifacts_matching_configured_exclude(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["copyfileartifacts"]["exclude"] = "artifact2.file"

        self._run_importer()

        self.assert_number_of_files_in_dir(
            2, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact2.file"
        )
        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file2"
        )
        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file3"
        )

    def test_only_copy_artifacts_matching_configured_filename(self):
        config["copyfileartifacts"]["extensions"] = ""
        config["copyfileartifacts"]["filenames"] = "artifact.file"

        self._run_importer()

        self.assert_number_of_files_in_dir(
            2, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact2.file"
        )
        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file2"
        )
        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file3"
        )

    def test_only_copy_artifacts_matching_configured_extension_and_filename(
        self,
    ):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["copyfileartifacts"]["filenames"] = "artifact.file2"

        self._run_importer()

        self.assert_number_of_files_in_dir(
            4, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")

        self.assert_number_of_files_in_dir(5, self.import_dir, b"the_album")

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file3"
        )

    def test_copy_all_artifacts_by_default(self):
        self._run_importer()

        self.assert_number_of_files_in_dir(
            5, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file3")

    def test_copy_artifacts(self):
        self._run_importer()

        self.assert_number_of_files_in_dir(
            5, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file3")

    def test_ignore_media_files(self):
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.mp3")

    def test_move_artifacts(self):
        config["import"]["move"] = True

        self._run_importer()

        self.assert_number_of_files_in_dir(
            5, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file3")

        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact2.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact.file2")
        self.assert_not_in_import_dir(b"the_album", b"artifact.file3")

    def test_prune_import_directory_when_emptied(self):
        """
        Check that plugin does not interfere with normal
        pruning of emptied import directories.
        """
        config["import"]["move"] = True

        self._run_importer()

        self.assert_not_in_import_dir(b"the_album")

    def test_do_nothing_when_not_copying_or_moving(self):
        """
        Check that plugin leaves everything alone when not
        copying (-C command line option) and not moving.
        """
        config["import"]["copy"] = False
        config["import"]["move"] = False

        self._run_importer()

        self.assert_number_of_files_in_dir(5, self.import_dir, b"the_album")

        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_import_dir(b"the_album", b"artifact2.file")
        self.assert_in_import_dir(b"the_album", b"artifact.file2")
        self.assert_in_import_dir(b"the_album", b"artifact.file3")

    def test_rename_when_copying(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_in_import_dir(b"the_album", b"artifact.file")

    def test_rename_when_moving(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
