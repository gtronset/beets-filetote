# pylint: disable=duplicate-code

import os

import beets
from beets import config

from tests.helper import FiletoteTestCase


class FiletoteMoveOperation(FiletoteTestCase):
    """
    Tests to check handling of the operation (copy, move, etc.) can be
    overridden by the CLI.
    """

    def setUp(self):
        """Provides shared setup for tests."""
        super().setUp()

        self._set_import_dir()
        self.album_path = os.path.join(self.import_dir, b"the_album")
        self.rsrc_mp3 = b"full.mp3"
        os.makedirs(self.album_path)

        config["filetote"]["extensions"] = ".file"

    def test_import_config_copy_false_import_op_copy(self):
        """Tests that when config does not have an operation set, that
        providing it as `--copy` in the CLI correctly overrides."""

        self._setup_import_session(copy=False, autotag=False)

        self._create_file(
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

    def test_import_config_copy_false_import_op_move(self):
        """Tests that when config does not have an operation set, that
        providing it as `--move` in the CLI correctly overrides."""
        self._setup_import_session(copy=False, autotag=False)

        self._create_file(
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

    def test_import_config_copy_true_import_op_move(self):
        """Tests that when config operation is set to `copy`, that providing
        `--move` in the CLI correctly overrides."""

        self._setup_import_session(copy=True, autotag=False)

        self._create_file(
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

    def test_import_config_move_true_import_op_copy(self):
        """Tests that when config operation is set to `move`, that providing
        `--copy` in the CLI correctly overrides."""
        self._setup_import_session(move=True, autotag=False)

        self._create_file(
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
