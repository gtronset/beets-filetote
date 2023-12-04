"""Tests CLI operations supersede config for the beets-filetote plugin."""

# pylint: disable=duplicate-code

import os
from typing import List, Optional

import beets
from beets import config

from tests.helper import FiletoteTestCase


class FiletoteCLIOperation(FiletoteTestCase):
    """
    Tests to check handling of the operation (copy, move, etc.) can be
    overridden by the CLI.
    """

    def setUp(self, other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._set_import_dir()
        self.album_path = os.path.join(self.import_dir, b"the_album")
        self.rsrc_mp3 = b"full.mp3"
        os.makedirs(self.album_path)

        self._base_file_count: int = 0

        config["filetote"]["extensions"] = ".file"

    def test_do_nothing_when_not_copying_or_moving(self) -> None:
        """
        Check that plugin leaves everything alone when not
        copying (-C command line option) and not moving.
        """
        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

        self._base_file_count = self._media_count + self._pairs_count

        config["import"]["copy"] = False
        config["import"]["move"] = False

        self._run_importer()

        self.assert_number_of_files_in_dir(
            self._base_file_count + 4, self.import_dir, b"the_album"
        )

        self.assert_in_import_dir(b"the_album", b"artifact.file")
        self.assert_in_import_dir(b"the_album", b"artifact2.file")
        self.assert_in_import_dir(b"the_album", b"artifact.nfo")
        self.assert_in_import_dir(b"the_album", b"artifact.lrc")

    def test_import_config_copy_false_import_on_copy(self) -> None:
        """Tests that when config does not have an operation set, that
        providing it as `--copy` in the CLI correctly overrides."""

        self._setup_import_session(copy=False, autotag=False)

        self.create_file(
            self.album_path, beets.util.bytestring_path("\xe4rtifact.file")
        )
        medium = self._create_medium(
            os.path.join(self.album_path, b"track_1.mp3"), self.rsrc_mp3
        )
        self.import_media = [medium]

        self._run_importer(operation_option="copy")

        self.assert_in_import_dir(
            b"the_album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

    def test_import_config_copy_false_import_on_move(self) -> None:
        """Tests that when config does not have an operation set, that
        providing it as `--move` in the CLI correctly overrides."""
        self._setup_import_session(copy=False, autotag=False)

        self.create_file(
            self.album_path, beets.util.bytestring_path("\xe4rtifact.file")
        )
        medium = self._create_medium(
            os.path.join(self.album_path, b"track_1.mp3"), self.rsrc_mp3
        )
        self.import_media = [medium]

        self._run_importer(operation_option="move")

        self.assert_not_in_import_dir(
            b"the_album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

    def test_import_config_copy_true_import_on_move(self) -> None:
        """Tests that when config operation is set to `copy`, that providing
        `--move` in the CLI correctly overrides."""

        self._setup_import_session(copy=True, autotag=False)

        self.create_file(
            self.album_path, beets.util.bytestring_path("\xe4rtifact.file")
        )
        medium = self._create_medium(
            os.path.join(self.album_path, b"track_1.mp3"), self.rsrc_mp3
        )
        self.import_media = [medium]

        self._run_importer(operation_option="move")

        self.assert_not_in_import_dir(
            b"the_album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

    def test_import_config_move_true_import_on_copy(self) -> None:
        """Tests that when config operation is set to `move`, that providing
        `--copy` in the CLI correctly overrides."""
        self._setup_import_session(move=True, autotag=False)

        self.create_file(
            self.album_path, beets.util.bytestring_path("\xe4rtifact.file")
        )
        medium = self._create_medium(
            os.path.join(self.album_path, b"track_1.mp3"), self.rsrc_mp3
        )
        self.import_media = [medium]

        self._run_importer(operation_option="copy")

        self.assert_in_import_dir(
            b"the_album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            beets.util.bytestring_path("\xe4rtifact.file"),
        )

    def test_move_on_move_command(self) -> None:
        """
        Check that plugin detects the correct operation for the "move" (or "mv")
        command, which is MOVE by default.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        self.lib.path_formats = [
            ("default", os.path.join("Old Lib Artist", "$album", "$title")),
        ]

        self._run_importer()

        self.lib.path_formats = [
            ("default", os.path.join("$artist", "$album", "$title")),
        ]

        self._run_mover(query="artist:'Tag Artist'")

        self.assert_not_in_lib_dir(
            b"Old Lib Artist",
            b"Tag Album",
            b"artifact.file",
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

    def test_copy_on_move_command_copy(self) -> None:
        """
        Check that plugin detects the correct operation for the "move" (or "mv")
        command when "copy" is set. The files should be present in both the original
        and new Library locations.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        self.lib.path_formats = [
            ("default", os.path.join("Old Lib Artist", "$album", "$title")),
        ]

        self._run_importer()

        self.lib.path_formats = [
            ("default", os.path.join("$artist", "$album", "$title")),
        ]

        self._run_mover(query="artist:'Tag Artist'", copy=True)

        self.assert_in_lib_dir(b"Old Lib Artist", b"Tag Album", b"artifact.file")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

    def test_copy_on_move_command_export(self) -> None:
        """
        Check that plugin detects the correct operation for the "move" (or "mv")
        command when "export" is set. This functionally is the same as "copy" but
        does not alter the Library data.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        self.lib.path_formats = [
            ("default", os.path.join("Old Lib Artist", "$album", "$title")),
        ]

        self._run_importer()

        self.lib.path_formats = [
            ("default", os.path.join("$artist", "$album", "$title")),
        ]

        self._run_mover(query="artist:'Tag Artist'", export=True)

        self.assert_in_lib_dir(b"Old Lib Artist", b"Tag Album", b"artifact.file")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

    def test_move_on_modify_command(self) -> None:
        """
        Check that plugin detects the correct operation for the "move" (or "mv")
        command, which is MOVE by default.
        """
        self._create_flat_import_dir()

        self._setup_import_session(move=True, autotag=False)

        self.lib.path_formats = [
            ("default", os.path.join("Old Lib Artist", "$album", "$title")),
        ]

        self._run_importer()

        self.lib.path_formats = [
            ("default", os.path.join("$artist", "$album", "$title")),
        ]

        self._run_modify(query="artist:'Tag Artist'", mods={"artist": "Tag Artist New"})

        self.assert_not_in_lib_dir(
            b"Old Lib Artist",
            b"Tag Album",
            b"artifact.file",
        )

        self.assert_in_lib_dir(b"Tag Artist New", b"Tag Album", b"artifact.file")
