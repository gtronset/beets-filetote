"""Tests reimporting for the beets-filetote plugin."""

# pylint: disable=duplicate-code

import logging
import os

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteReimportTest(FiletoteTestCase):
    """
    Tests to check that Filetote handles reimports correctly
    """

    def setUp(self, audible_plugin: bool = False) -> None:
        """
        Setup subsequent import directory of the following structure:

            testlib_dir/
                Tag Artist/
                    Tag Album/
                        Tag Title 1.mp3
                        Tag Title 2.mp3
                        Tag Title 3.mp3
                        artifact.file
                        artifact2.file
        """
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False, move=True)

        config["filetote"]["extensions"] = ".file"

        log.debug("--- initial import")
        self._run_importer()

    def test_reimport_artifacts_with_copy(self) -> None:
        """Tests that when reimporting, copying works."""
        # Cause files to relocate (move) when reimported
        self.lib.path_formats[0] = (
            "default",
            os.path.join("1$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir)

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"1Tag Artist", b"Tag Album", b"artifact.file")

    def test_reimport_artifacts_with_move(self) -> None:
        """Tests that when reimporting, moving works."""
        # Cause files to relocate when reimported
        self.lib.path_formats[0] = (
            "default",
            os.path.join("1$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir, move=True)

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"1Tag Artist", b"Tag Album", b"artifact.file")

    def test_prune_empty_directories_with_copy_reimport(self) -> None:
        """
        Ensure directories are pruned when reimporting with 'copy'.
        """
        # Cause files to relocate when reimported
        self.lib.path_formats[0] = (
            "default",
            os.path.join("1$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir)

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"1Tag Artist", b"Tag Album", b"artifact.file")

    def test_do_nothing_when_paths_do_not_change_with_copy_import(self) -> None:
        """Tests that when paths are the same (before/after), no action is
        taken for default `copy` action."""
        self._setup_import_session(autotag=False, import_dir=self.lib_dir)

        log.debug("--- second import")
        self._run_importer()

        self.assert_number_of_files_in_dir(5, self.lib_dir, b"Tag Artist", b"Tag Album")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

    def test_do_nothing_when_paths_do_not_change_with_move_import(self) -> None:
        """Tests that when paths are the same (before/after), no action is
        taken for default `move` action."""
        self._setup_import_session(autotag=False, import_dir=self.lib_dir, move=True)

        log.debug("--- second import")
        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

    def test_rename_with_copy_reimport(self) -> None:
        """Tests that renaming during `copy` works even when reimporting."""
        config["paths"]["ext:file"] = os.path.join("$albumpath", "$artist - $album")
        self._setup_import_session(autotag=False, import_dir=self.lib_dir)

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )

    def test_rename_with_move_reimport(self) -> None:
        """Tests that renaming during `move` works even when reimporting."""
        config["paths"]["ext:file"] = os.path.join("$albumpath", "$artist - $album")
        self._setup_import_session(autotag=False, import_dir=self.lib_dir, move=True)

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )

    def test_rename_when_paths_do_not_change(self) -> None:
        """
        This test considers the situation where the path format for a file extension
        is changed and files already in the library are reimported and renamed to
        reflect the change
        """
        config["paths"]["ext:file"] = os.path.join("$albumpath", "$album")
        self._setup_import_session(autotag=False, import_dir=self.lib_dir, move=True)

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Album.file")

    def test_multiple_reimport_artifacts_with_move(self) -> None:
        """Tests that multiple reimports work the same as the initial action or
        a single reimport."""
        # Cause files to relocate when reimported
        self.lib.path_formats[0] = (
            "default",
            os.path.join("1$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir, move=True)
        config["paths"]["ext:file"] = "$albumpath/$old_filename - import I"

        log.debug("--- first import")
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(
            b"1Tag Artist", b"Tag Album", b"artifact - import I.file"
        )
        self.assert_in_lib_dir(
            b"1Tag Artist", b"Tag Album", b"artifact2 - import I.file"
        )

        log.debug("--- second import")
        self.lib.path_formats[0] = (
            "default",
            os.path.join("2$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir, move=True)
        config["paths"]["ext:file"] = "$albumpath/$old_filename I"
        self._run_importer()

        self.assert_not_in_lib_dir(
            b"1Tag Artist", b"Tag Album", b"artifact - import I.file"
        )
        self.assert_not_in_lib_dir(
            b"1Tag Artist", b"Tag Album", b"artifact2 - import I.file"
        )
        self.assert_in_lib_dir(
            b"2Tag Artist", b"Tag Album", b"artifact - import I I.file"
        )
        self.assert_in_lib_dir(
            b"2Tag Artist", b"Tag Album", b"artifact2 - import I I.file"
        )

        log.debug("--- third import")
        self.lib.path_formats[0] = (
            "default",
            os.path.join("3$artist", "$album", "$title"),
        )
        self._setup_import_session(autotag=False, import_dir=self.lib_dir, move=True)

        self._run_importer()

        self.assert_not_in_lib_dir(
            b"2Tag Artist", b"Tag Album", b"artifact - import I I.file"
        )
        self.assert_not_in_lib_dir(
            b"2Tag Artist", b"Tag Album", b"artifact2 - import I I.file"
        )
        self.assert_in_lib_dir(
            b"3Tag Artist", b"Tag Album", b"artifact - import I I I.file"
        )
        self.assert_in_lib_dir(
            b"3Tag Artist", b"Tag Album", b"artifact2 - import I I I.file"
        )

    def test_reimport_artifacts_with_query(self) -> None:
        """Tests that when reimporting, copying works."""
        # Cause files to relocate (move) when reimported
        self.lib.path_formats = [
            ("default", os.path.join("New Tag Artist", "$album", "$title")),
        ]
        self._setup_import_session(query="artist", autotag=False, move=True)

        log.debug("--- second import")
        self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"New Tag Artist", b"Tag Album", b"artifact.file")
