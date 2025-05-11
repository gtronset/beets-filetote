"""Tests renaming for the beets-filetote plugin."""

import logging
import os

from typing import List, Optional

import pytest

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteRenameTest(FiletoteTestCase):
    """Tests to check that Filetote renames as expected for custom path
    formats (both by extension and filename).
    """

    def setUp(self, _other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_rename_when_copying(self) -> None:
        """Tests that renaming works when copying."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/$artist - $album"

        self._run_cli_command("import")

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_when_moving(self) -> None:
        """Tests that renaming works when moving."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/$artist - $album"
        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")

    def test_rename_paired_ext(self) -> None:
        """Tests that the value of `medianame_new` populates in renaming."""
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"]["enabled"] = True
        config["paths"]["paired_ext:lrc"] = "$albumpath/$medianame_new"

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_paired_ext_does_not_conflict_with_ext(self) -> None:
        """Tests that paired path definitions work alongside `ext` ones."""
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"]["enabled"] = True
        config["paths"]["ext:lrc"] = "$albumpath/1 $old_filename"
        config["paths"]["paired_ext:lrc"] = "$albumpath/$medianame_new"

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"1 artifact.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_paired_ext_is_prioritized_over_ext(self) -> None:
        """Tests that paired path definitions supersede `ext` ones when there's
        a collision.
        """
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"]["enabled"] = True
        config["paths"]["paired_ext:lrc"] = "$albumpath/$medianame_new"
        config["paths"]["ext:lrc"] = "$albumpath/1 $old_filename"

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"1 artifact.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_filename_is_prioritized_over_paired_ext(self) -> None:
        """Tests that filename path definitions supersede `paired` ones when there's
        a collision.
        """
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"]["enabled"] = True
        config["paths"]["paired_ext:lrc"] = "$albumpath/$medianame_new"
        config["paths"]["filename:track_1.lrc"] = "$albumpath/1 $old_filename"

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"1 track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_period_is_optional_for_ext(self) -> None:
        """Tests that leading periods are options when definiting `ext` paths."""
        config["filetote"]["extensions"] = ".file .nfo"
        config["paths"]["ext:file"] = "$albumpath/$artist - $album"
        config["paths"]["ext:.nfo"] = "$albumpath/$artist - $album 2"
        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album 2.nfo"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact.nfo")

    def test_rename_ignores_file_when_name_conflicts(self) -> None:
        """Ensure that if there are multiple files that would rename to the
        exact same name, that only the first is renamed (moved/copied/etc.)
        but not subsequent ones that conflict.
        """
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/$artist - $album"
        config["import"]["move"] = True

        self._run_cli_command("import")

        # `artifact.file` correctly renames.
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - Tag Album.file"
        )

        # `artifact2.file` will not rename since the destination filename conflicts with
        # `artifact.file`
        self.assert_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_multiple_extensions(self) -> None:
        """Ensure that specifying multiple extensions and definitions properly
        rename.
        """
        config["filetote"]["extensions"] = ".file .nfo"
        config["paths"]["ext:file"] = "$albumpath/$artist - $album"
        config["paths"]["ext:nfo"] = "$albumpath/$artist - $album"
        config["import"]["move"] = True

        self._run_cli_command("import")

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

    def test_rename_matching_filename(self) -> None:
        """Ensure that `filename` path definitions rename correctly."""
        config["filetote"]["filenames"] = "artifact.file artifact2.file"
        config["paths"]["filename:artifact.file"] = "$albumpath/new-filename"
        config["paths"]["filename:artifact2.file"] = "$albumpath/another-new-filename"
        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"new-filename.file")
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"another-new-filename.file"
        )
        self.assert_not_in_import_dir(b"the_album", b"artifact.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_prioritizes_filename_over_ext(self) -> None:
        """Tests that filename path definitions supersede `ext` ones when there's
        a collision.
        """
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["filenames"] = "artifact.file"
        config["paths"]["ext:file"] = "$albumpath/$artist - $old_filename"
        config["paths"]["filename:artifact.file"] = "$albumpath/new-filename"
        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"new-filename.file")
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - artifact2.file"
        )

        self.assert_not_in_import_dir(b"the_album", b"artifact1.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_prioritizes_filename_over_ext_reversed(self) -> None:
        """Ensure the order of path definitions does not effect the priority
        order.
        """
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["filenames"] = "artifact.file"
        # order of paths matter here; this is the opposite order as
        # `test_rename_prioritizes_filename_over_ext`
        config["paths"]["filename:artifact.file"] = "$albumpath/new-filename"
        config["paths"]["ext:file"] = "$albumpath/$artist - $old_filename"
        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"new-filename.file")
        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Tag Artist - artifact2.file"
        )

        self.assert_not_in_import_dir(b"the_album", b"artifact1.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_multiple_files_prioritizes_filename_over_ext(self) -> None:
        """Tests that multiple filename path definitions still supersede `ext`
        ones when there's collision(s).
        """
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["filenames"] = "artifact.file artifact2.file"
        config["paths"]["ext:file"] = "$albumpath/$artist - $old_filename"
        config["paths"]["filename:artifact.file"] = "$albumpath/new-filename"
        config["paths"]["filename:artifact2.file"] = "$albumpath/new-filename2"
        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"new-filename.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"new-filename2.file")

        self.assert_not_in_import_dir(b"the_album", b"artifact1.file")
        self.assert_not_in_import_dir(b"the_album", b"artifact2.file")

    def test_rename_wildcard_extension_halts(self) -> None:
        """Ensure that specifying `ext:.*` extensions results in an exception."""
        config["filetote"]["extensions"] = ".file .nfo"
        config["paths"]["ext:.*"] = "$albumpath/$old_filename"
        config["import"]["move"] = True

        with pytest.raises(AssertionError) as assert_test_message:
            self._run_cli_command("import")

        assertion_msg: str = (
            "Error: path query `ext:.*` is not valid. If you are"
            " trying to set a default/fallback, please user `filetote:default` instead."
        )

        assert str(assert_test_message.value) == assertion_msg

    def test_rename_filetote_paths_wildcard_extension_halts(self) -> None:
        """Ensure that specifying `ext:.*` extensions results in an exception."""
        config["filetote"]["extensions"] = ".file .nfo"
        config["filetote"]["paths"]["ext:.*"] = "$albumpath/$old_filename"
        config["import"]["move"] = True

        with pytest.raises(AssertionError) as assert_test_message:
            self._run_cli_command("import")

        assertion_msg: str = (
            "Error: path query `ext:.*` is not valid. If you are"
            " trying to set a default/fallback, please user `filetote:default` instead."
        )

        assert str(assert_test_message.value) == assertion_msg

    def test_rename_filetote_default(self) -> None:
        """Ensure that the default value for a path query of an otherwise not specified
        artifact is `$albumpath/$old_filename`.
        """
        config["filetote"]["extensions"] = ".file"
        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

    def test_rename_filetote_custom_default(self) -> None:
        """Ensure that the default value for a path query for artifacts
        (`filetote:default`) can be updated via the root `paths` setting.
        """
        config["filetote"]["extensions"] = ".file"

        config["paths"]["filetote:default"] = os.path.join(
            "$albumpath", "New", "$old_filename"
        )

        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"New", b"artifact.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

    def test_rename_filetote_custom_default_filetote_paths(self) -> None:
        """Ensure that the default value for a path query for artifacts
        (`filetote:default`) can be updated via the Filetote `paths` setting.
        """
        config["filetote"]["extensions"] = ".file"

        config["filetote"]["paths"]["filetote:default"] = os.path.join(
            "$albumpath", "New", "$old_filename"
        )

        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"New", b"artifact.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

    def test_rename_filetote_custom_default_priority(self) -> None:
        """Ensure that the default value for a path query for artifacts
        (`filetote:default`) prioritizes the Filetote `paths` setting over the
        root `paths` setting.
        """
        config["filetote"]["extensions"] = ".file"

        config["paths"]["filetote:default"] = os.path.join(
            "$albumpath", "Paths", "$old_filename"
        )
        config["filetote"]["paths"]["filetote:default"] = os.path.join(
            "$albumpath", "Filetote", "$old_filename"
        )

        config["import"]["move"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"Filetote", b"artifact.file"
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
