import os
import sys

from tests.helper import CopyFileArtifactsTestCase
from beets import config


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

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")

    def test_copy_all_artifacts_by_default(self):
        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")

    def test_copy_artifacts(self):
        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")

    def test_ignore_media_files(self):
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.mp3")

    def test_move_artifacts(self):
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact.file2")

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
        Check that plugin leaves everthing alone when not
        copying (-C command line option) and not moving.
        """
        config["import"]["copy"] = False
        config["import"]["move"] = False

        self._run_importer()

        self.assert_number_of_files_in_dir(3, self.import_dir, b"the_album")
        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_import_dir(b"the_album", b"artifact.file2")

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
