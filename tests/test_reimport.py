import logging
import os
import sys
import unittest

from beets import config

from tests.helper import CopyFileArtifactsTestCase

log = logging.getLogger("beets")


class CopyFileArtifactsReimportTest(CopyFileArtifactsTestCase):
    """
    Tests to check that copyfileartifacts handles reimports correctly
    """

    def setUp(self):
        """
        Setup an import directory of the following structure:

            testlib_dir/
                Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        artifact.file
                        artifact2.file
        """
        super(CopyFileArtifactsReimportTest, self).setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".file"

        log.debug("--- initial import")
        self._run_importer()

    def test_reimport_artifacts_with_copy(self):
        # Cause files to relocate when reimported
        self.lib.path_formats[0] = (
            "default",
            os.path.join("1$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir)

        log.debug("--- second import")
        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"1Tag Artist", b"Tag Album", b"artifact.file")

    def test_reimport_artifacts_with_move(self):
        # Cause files to relocate when reimported
        self.lib.path_formats[0] = (
            "default",
            os.path.join("1$artist", "$album", "$title"),
        )
        self._setup_import_session(
            autotag=False, import_dir=self.lib_dir, move=True
        )

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file"
        )
        self.assert_in_lib_dir(b"1Tag Artist", b"Tag Album", b"artifact.file")

    def test_prune_empty_directories_with_copy_import(self):
        """
        No directories are pruned when importing with 'copy'. Test is
        identical to test_reimport_artifacts_with_copy, included for
        completeness.
        """
        # Cause files to relocate when reimported
        self.lib.path_formats[0] = (
            "default",
            os.path.join("1$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir)

        log.debug("--- second import")
        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"1Tag Artist", b"Tag Album", b"artifact.file")

    @unittest.skip("Failing")
    def test_prune_empty_directories_with_move_import(self):
        # Cause files to relocate when reimported
        self.lib.path_formats[0] = (
            "default",
            os.path.join("1$artist", "$album", "$title"),
        )
        self._setup_import_session(
            autotag=False, import_dir=self.lib_dir, move=True
        )

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist")
        self.assert_in_lib_dir(b"1Tag Artist", b"Tag Album", b"artifact.file")

    def test_do_nothing_when_paths_do_not_change_with_copy_import(self):
        self._setup_import_session(autotag=False, import_dir=self.lib_dir)

        log.debug("--- second import")
        self._run_importer()

        self.assert_number_of_files_in_dir(
            3, self.lib_dir, b"Tag Artist", b"Tag Album"
        )
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

    def test_do_nothing_when_paths_do_not_change_with_move_import(self):
        self._setup_import_session(
            autotag=False, import_dir=self.lib_dir, move=True
        )

        log.debug("--- second import")
        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

    def test_rename_with_copy_import(self):
        config["paths"]["ext:file"] = str(
            os.path.join("$albumpath", "$artist - $album")
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir)

        log.debug("--- second import")
        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )

    def test_rename_with_move_import(self):
        config["paths"]["ext:file"] = str(
            os.path.join("$albumpath", "$artist - $album")
        )
        self._setup_import_session(
            autotag=False, import_dir=self.lib_dir, move=True
        )

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )

    def test_rename_when_paths_do_not_change(self):
        """
        This test considers the situation where the path format for a file extension
        is changed and files already in the library are reimported and renamed to
        reflect the change
        """
        config["paths"]["ext:file"] = str(os.path.join("$albumpath", "$album"))
        self._setup_import_session(
            autotag=False, import_dir=self.lib_dir, move=True
        )

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file"
        )
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Album.file")

    @unittest.skip("Todo")
    def test_multiple_reimport_artifacts_with_move(self):
        # Cause files to relocate when reimported
        # self.lib.path_formats[0] = ('default', os.path.join('1$artist', '$album', '$title'))
        config["paths"]["ext:file"] = str(os.path.join("$albumpath", "$album"))
        self._setup_import_session(
            autotag=False, import_dir=self.lib_dir, move=True
        )

        album_path = os.path.join(self.lib_dir, b"Tag Artist", b"Tag Album")
        log.debug("@@@@@@@@@@@@@@")
        log.debug(album_path)
        open(os.path.join(album_path, b"artifact2.file"), "a").close()

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file"
        )
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Album.file")

        log.debug("--- third import")
        self._run_importer()

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file"
        )
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Album.file")
