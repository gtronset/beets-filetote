"""Tests renaming Filetote custom fields for the beets-filetote plugin."""

import logging
import os

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteRenameFiletoteFieldsTest(FiletoteTestCase):
    """Tests to check that Filetote renames using Filetote-provided fields as
    expected for custom path formats.
    """

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir(pair_subfolders=True)
        self._setup_import_session(autotag=False, move=True)

    def test_rename_field_albumpath(self) -> None:
        """Tests that the value of `albumpath` populates in renaming."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/newname"

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"newname.file")

    def test_rename_field_old_filename(self) -> None:
        """Tests that the value of `old_filename` populates in renaming."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/$old_filename"

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

    def test_rename_field_medianame_old(self) -> None:
        """Tests that the value of `medianame_old` populates in renaming."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/$medianame_old"

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.file")

    def test_rename_field_medianame_new(self) -> None:
        """Tests that the value of `medianame_new` populates in renaming."""
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }
        config["paths"]["ext:lrc"] = "$albumpath/$medianame_new"

        self._run_cli_command("import")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"Tag Title 3.lrc")

    def test_rename_field_subpath(self) -> None:
        """Tests that the value of `subpath` populates in renaming. Also tests that the
        default lyric file moves as expected without a trailing pah separator.
        """
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"]["enabled"] = True

        config["paths"]["ext:lrc"] = os.path.join(
            "$albumpath", "$subpath$medianame_new"
        )

        self._run_cli_command("import")

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"lyrics",
            b"lyric-subfolder",
            b"Tag Title 1.lrc",
        )
        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"lyrics",
            b"lyric-subfolder",
            b"Tag Title 2.lrc",
        )
        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"lyrics",
            b"lyric-subfolder",
            b"Tag Title 3.lrc",
        )
