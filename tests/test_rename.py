# pylint: disable=too-many-public-methods

import logging

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteRenameTest(FiletoteTestCase):
    """
    Tests to check that Filetote renames as expected for custom path
    formats (both by extension and filename).
    """

    def setUp(self):
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_rename_field_albumpath(self):
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/newname")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"newname.file")

    def test_rename_field_artist(self):
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - newname")

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - newname.file"
        )

    def test_rename_field_albumartist(self):
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$albumartist - newname")

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Album Artist - newname.file"
        )

    def test_rename_field_album(self):
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$album - newname")

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Album - newname.file"
        )

    def test_rename_field_old_filename(self):
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$old_filename")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

    def test_rename_field_medianame_old(self):
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$medianame_old")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.file")

    def test_rename_paired_ext(self):
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True
        config["filetote"]["paring_only"] = True
        config["paths"]["paired_ext:lrc"] = str("$albumpath/$medianame_new")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_paired_ext_does_not_conflict_with_ext(self):
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True
        config["filetote"]["paring_only"] = True
        config["paths"]["ext:lrc"] = str("$albumpath/1 $old_filename")
        config["paths"]["paired_ext:lrc"] = str("$albumpath/$medianame_new")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"1 artifact.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_paired_ext_is_prioritized_over_ext(self):
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True
        config["filetote"]["paring_only"] = True
        config["paths"]["paired_ext:lrc"] = str("$albumpath/$medianame_new")
        config["paths"]["ext:lrc"] = str("$albumpath/1 $old_filename")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"1 artifact.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_filename_is_prioritized_over_paired_ext(self):
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True
        config["filetote"]["paring_only"] = True
        config["paths"]["paired_ext:lrc"] = str("$albumpath/$medianame_new")
        config["paths"]["filename:track_1.lrc"] = str(
            "$albumpath/1 $old_filename"
        )

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"1 track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_field_medianame_new(self):
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True
        config["filetote"]["paring_only"] = True
        config["paths"]["ext:lrc"] = str("$albumpath/$medianame_new")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_when_copying(self):
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_when_moving(self):
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")

    def test_rename_period_is_optional_for_ext(self):
        config["filetote"]["extensions"] = ".file .nfo"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")
        config["paths"]["ext:.nfo"] = str("$albumpath/$artist - $album 2")
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album 2.nfo"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact.nfo")

    def test_rename_ignores_file_when_name_conflicts(self):
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        # `artifact2.file` will rename since the destination filename conflicts with
        # `artifact.file`
        self.assert_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_multiple_extensions(self):
        config["filetote"]["extensions"] = ".file .nfo"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $album")
        config["paths"]["ext:nfo"] = str("$albumpath/$artist - $album")
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.nfo"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact.nfo")
        # `artifact2.file` will rename since the destination filename conflicts with
        #  `artifact.file`
        self.assert_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_matching_filename(self):
        config["filetote"]["filenames"] = "artifact.file artifact2.file"
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
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["filenames"] = "artifact.file"
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

    def test_rename_prioritizes_filename_over_ext_reversed(self):
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["filenames"] = "artifact.file"
        # order of paths matter here; this is the opposite order as
        # `test_rename_prioritizes_filename_over_ext`
        config["paths"]["filename:artifact.file"] = str(
            "$albumpath/new-filename"
        )
        config["paths"]["ext:file"] = str("$albumpath/$artist - $old_filename")
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

    def test_rename_multiple_files_prioritizes_filename_over_ext(self):
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["filenames"] = "artifact.file artifact2.file"
        config["paths"]["ext:file"] = str("$albumpath/$artist - $old_filename")
        config["paths"]["filename:artifact.file"] = str(
            "$albumpath/new-filename"
        )
        config["paths"]["filename:artifact2.file"] = str(
            "$albumpath/new-filename2"
        )
        config["import"]["move"] = True

        self._run_importer()

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"new-filename.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"new-filename2.file"
        )

        self.assert_not_in_import_dir(b"the_album", b"artifact1.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact2.file")
