"""Tests manipulation of files for the beets-filetote plugin."""

from typing import TYPE_CHECKING

import pytest

from tests.pytest_beets_plugin import BeetsPluginFixture

if TYPE_CHECKING:
    from pathlib import Path


class TestManipulateFiles:
    """Tests to check that Filetote manipulates files using the correct operation."""

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: BeetsPluginFixture) -> None:
        """Provides shared setup for tests."""
        self.env = beets_plugin_env

        self.env.create_flat_import_dir()
        self.env.setup_import_session(autotag=False, copy=False)

    def test_copy_artifacts(self) -> None:
        """Test that copy actually copies (and not just moves)."""
        env = self.env

        env.config["import"]["copy"] = True
        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count + env.pairs_count + 4,
            env.lib_dir / "Tag Artist" / "Tag Album",
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_move_artifacts(self) -> None:
        """Test that move actually moves (and not just copies)."""
        env = self.env
        env.config["import"]["move"] = True
        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count + env.pairs_count + 4,
            env.lib_dir / "Tag Artist" / "Tag Album",
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

        env.assert_not_in_import_dir("the_album/artifact.file")
        env.assert_not_in_import_dir("the_album/artifact2.file")
        env.assert_not_in_import_dir("the_album/artifact.nfo")
        env.assert_not_in_import_dir("the_album/artifact.lrc")

    def test_artifacts_copymove_on_first_media_by_default(self) -> None:
        """By default, all eligible files are grabbed with the first item."""
        env = self.env
        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/$medianame_old - $old_filename"

        env.config["import"]["copy"] = True

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1 - artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1 - artifact2.file")

    @pytest.mark.needs_symlink
    def test_import_symlink_files(self) -> None:
        """Tests that the `symlink` operation correctly symlinks files."""
        env = self.env
        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/newname"
        env.config["import"]["link"] = True

        old_path: Path = env.import_dir / "the_album" / "artifact.file"
        new_path: Path = env.lib_dir / "Tag Artist" / "Tag Album" / "newname.file"

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/newname.file")

        env.assert_islink("Tag Artist/Tag Album/newname.file")

        env.assert_equal_path(new_path, old_path)

    @pytest.mark.needs_hardlink
    def test_import_hardlink_files(self) -> None:
        """Tests that the `hardlink` operation correctly hardlinks files."""
        env = self.env
        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/newname"
        env.config["import"]["hardlink"] = True

        old_path: Path = env.import_dir / "the_album" / "artifact.file"
        new_path: Path = env.lib_dir / "Tag Artist" / "Tag Album" / "newname.file"

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/newname.file")

        old_stat = old_path.stat()
        new_stat = new_path.stat()

        assert (old_stat.st_ino, old_stat.st_dev) == (new_stat.st_ino, new_stat.st_dev)

    @pytest.mark.needs_reflink
    def test_import_reflink_files(self) -> None:
        """Tests that the `reflink` operation correctly links files."""
        env = self.env
        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/newname"
        env.config["import"]["reflink"] = True

        old_path: Path = env.import_dir / "the_album" / "artifact.file"
        new_path: Path = env.lib_dir / "Tag Artist" / "Tag Album" / "newname.file"

        env.run_cli_command("import")

        old_stat = old_path.stat()
        new_stat = new_path.stat()

        # Reflinks have distinct inodes!
        assert old_stat.st_ino != new_stat.st_ino

        env.assert_in_import_dir("the_album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/newname.file")
