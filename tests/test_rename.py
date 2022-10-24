import logging
import os
import sys

from beets import config

from tests.helper import CopyFileArtifactsTestCase

log = logging.getLogger("beets")


class CopyFileArtifactsRenameTest(CopyFileArtifactsTestCase):
    """
    Tests to check that copyfileartifacts renames as expected for custom path
    formats (both by extension and filename).
    """

    def setUp(self):
        super(CopyFileArtifactsRenameTest, self).setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_rename_field_albumpath(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/newname")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"newname.file")

    def test_rename_field_artist(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - newname")

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - newname.file"
        )

    def test_rename_field_albumartist(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$albumartist - newname")

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Album Artist - newname.file"
        )

    def test_rename_field_album(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$album - newname")

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Album - newname.file"
        )

    def test_rename_field_old_filename(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$old_filename")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

    def test_rename_field_item_old_filename(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$item_old_filename")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.file")

    def test_rename_when_copying(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_when_moving(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")

    def test_rename_ignores_file_when_name_conflicts(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        # `artifact2.file` will rename since the destination filename conflicts with `artifact.file`
        self.assert_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_multiple_extensions(self):
        config["copyfileartifacts"]["extensions"] = ".file .file2"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")
        config["paths"]["ext:file2"] = str("$albumpath/$artist - $album")
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file2"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact.file2")
        # `artifact2.file` will rename since the destination filename conflicts with `artifact.file`
        self.assert_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_matching_filename(self):
        config["copyfileartifacts"][
            "filenames"
        ] = "artifact.file artifact2.file"
        config["paths"]["filename:artifact.file"] = str(
            "$albumpath/new-filename"
        )
        config["paths"]["filename:artifact2.file"] = str(
            "$albumpath/another-new-filename"
        )
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"new-filename.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"another-new-filename.file"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_prioritizes_filename_over_ext(self):
        config["copyfileartifacts"]["extensions"] = ".file"
        config["copyfileartifacts"]["filenames"] = "artifact.file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $old_filename")
        config["paths"]["filename:artifact.file"] = str(
            "$albumpath/new-filename"
        )
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"new-filename.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - artifact2.file"
        )

        self.assert_not_in_import_dir(b"the_album", b"artifact1.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact2.file")