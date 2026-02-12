"""Tests manipulation of files for the beets-filetote plugin."""

import logging
import os
import stat

from typing import TYPE_CHECKING

import pytest

from beets import config

from tests import _common
from tests.helper import FiletoteTestCase

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger("beets")


class FiletoteManipulateFiles(FiletoteTestCase):
    """Tests to check that Filetote manipulates files using the correct operation."""

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False, copy=False)

        self._base_file_count = self._media_count + self._pairs_count

    def test_copy_artifacts(self) -> None:
        """Test that copy actually copies (and not just moves)."""
        config["import"]["copy"] = True
        config["filetote"]["extensions"] = ".*"

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            self._base_file_count + 4, self.lib_dir / "Tag Artist" / "Tag Album"
        )

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_move_artifacts(self) -> None:
        """Test that move actually moves (and not just copies)."""
        config["import"]["move"] = True
        config["filetote"]["extensions"] = ".*"

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            self._base_file_count + 4, self.lib_dir / "Tag Artist" / "Tag Album"
        )

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

        self.assert_not_in_import_dir("the_album/artifact.file")
        self.assert_not_in_import_dir("the_album/artifact2.file")
        self.assert_not_in_import_dir("the_album/artifact.nfo")
        self.assert_not_in_import_dir("the_album/artifact.lrc")

    def test_artifacts_copymove_on_first_media_by_default(self) -> None:
        """By default, all eligible files are grabbed with the first item."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/$medianame_old - $old_filename"

        config["import"]["copy"] = True

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/track_1 - artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/track_1 - artifact2.file")

    @pytest.mark.skipif(not _common.HAVE_SYMLINK, reason="need symlinks")
    def test_import_symlink_files(self) -> None:
        """Tests that the `symlink` operation correctly symlinks files."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/newname"
        config["import"]["link"] = True

        old_path: Path = self.import_dir / "the_album" / "artifact.file"

        new_path: Path = self.lib_dir / "Tag Artist" / "Tag Album" / "newname.file"

        self._run_cli_command("import")

        self.assert_in_import_dir("the_album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/newname.file")

        self.assert_islink("Tag Artist/Tag Album/newname.file")

        self.assert_equal_path(new_path, old_path)

    @pytest.mark.skipif(not _common.HAVE_HARDLINK, reason="need hardlinks")
    def test_import_hardlink_files(self) -> None:
        """Tests that the `hardlink` operation correctly hardlinks files."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/newname"
        config["import"]["hardlink"] = True

        old_path: Path = self.import_dir / "the_album" / "artifact.file"

        new_path: Path = self.lib_dir / "Tag Artist" / "Tag Album" / "newname.file"

        self._run_cli_command("import")

        self.assert_in_import_dir("the_album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/newname.file")

        stat_old_path = os.stat(old_path)
        stat_new_path = os.stat(new_path)

        assert (stat_old_path[stat.ST_INO], stat_old_path[stat.ST_DEV]) == (
            stat_new_path[stat.ST_INO],
            stat_new_path[stat.ST_DEV],
        )

    @pytest.mark.skipif(not _common.HAVE_REFLINK, reason="need reflinks")
    def test_import_reflink_files(self) -> None:
        """Tests that the `reflink` operation correctly links files."""
        config["filetote"]["extensions"] = ".file"
        config["paths"]["ext:file"] = "$albumpath/newname"
        config["import"]["reflink"] = True

        self._run_cli_command("import")

        self.assert_in_import_dir("the_album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/newname.file")
