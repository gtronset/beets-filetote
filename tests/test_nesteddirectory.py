"""Tests nested directories for the beets-filetote plugin."""

import logging
import os

import pytest

from beets import config

from tests import _common
from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteFromNestedDirectoryTest(FiletoteTestCase):
    """Tests to check that Filetote copies or moves artifact files from a nested
    directory structure. i.e. songs in an album are imported from two directories
    corresponding to disc numbers or flat option is used.
    """

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_nested_import_dir()
        self._setup_import_session(autotag=False)

        self._base_file_count = self._media_count + self._pairs_count

    def test_copies_file_from_nested_to_library(self) -> None:
        """Ensures that nested directories are handled by beets and the the files
        relocate as expected following the default beets behavior (moves to a
        single directory).
        """
        config["filetote"]["extensions"] = ".file"

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            self._media_count + 4, self.lib_dir / "Tag Artist" / "Tag Album"
        )

        self.assert_in_lib_dir("Tag Artist", "Tag Album", "artifact.file")
        self.assert_in_lib_dir("Tag Artist", "Tag Album", "artifact2.file")
        self.assert_in_lib_dir("Tag Artist", "Tag Album", "artifact3.file")
        self.assert_in_lib_dir("Tag Artist", "Tag Album", "artifact4.file")

        self.assert_in_import_dir("the_album", "disc1", "artifact_disc1.nfo")
        self.assert_in_import_dir("the_album", "disc2", "artifact_disc2.nfo")

        self.assert_not_in_lib_dir("Tag Artist", "Tag Album", "artifact_disc1.nfo")
        self.assert_not_in_lib_dir("Tag Artist", "Tag Album", "artifact_disc2.lrc")

    def test_copies_file_from_nested_to_nested_library(self) -> None:
        """Ensures that nested directory artifacts are relocated as expected
        when beets is set to use a nested library destination.
        """
        config["filetote"]["extensions"] = ".file"
        self.lib.path_formats = [
            ("default", os.path.join("$artist", "$album", "$disc", "$title")),
        ]

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            5, self.lib_dir / "Tag Artist" / "Tag Album" / "01"
        )
        self.assert_number_of_files_in_dir(
            5, self.lib_dir / "Tag Artist" / "Tag Album" / "02"
        )

        self.assert_in_lib_dir("Tag Artist", "Tag Album", "01", "artifact.file")
        self.assert_in_lib_dir("Tag Artist", "Tag Album", "01", "artifact2.file")
        self.assert_in_lib_dir("Tag Artist", "Tag Album", "02", "artifact3.file")
        self.assert_in_lib_dir("Tag Artist", "Tag Album", "02", "artifact4.file")

        self.assert_in_import_dir("the_album", "disc1", "artifact_disc1.nfo")
        self.assert_in_import_dir("the_album", "disc2", "artifact_disc2.nfo")

        self.assert_not_in_lib_dir(
            "Tag Artist", "Tag Album", "01", "artifact_disc1.nfo"
        )
        self.assert_not_in_lib_dir(
            "Tag Artist", "Tag Album", "02", "artifact_disc2.lrc"
        )

    @pytest.mark.skipif(_common.PLATFORM == "win32", reason="win32")
    def test_copies_file_navigate_in_nested_library(self) -> None:
        """Ensures that nested directory artifacts are relocated using `..` without
        issue. This is skipped in Windows since `..` is taken literally instead of as
        a path component.
        """
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["paths"] = {
            "ext:file": os.path.join("$albumpath", "..", "artifacts", "$old_filename"),
        }

        self.lib.path_formats = [
            ("default", os.path.join("$artist", "$album", "$disc", "$title")),
        ]

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            3, self.lib_dir / "Tag Artist" / "Tag Album" / "01"
        )
        self.assert_number_of_files_in_dir(
            3, self.lib_dir / "Tag Artist" / "Tag Album" / "02"
        )

        self.assert_in_lib_dir("Tag Artist", "Tag Album", "artifacts", "artifact.file")
        self.assert_in_lib_dir("Tag Artist", "Tag Album", "artifacts", "artifact2.file")
        self.assert_in_lib_dir("Tag Artist", "Tag Album", "artifacts", "artifact3.file")
        self.assert_in_lib_dir("Tag Artist", "Tag Album", "artifacts", "artifact4.file")
