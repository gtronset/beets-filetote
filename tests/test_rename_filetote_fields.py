"""Tests renaming Filetote custom fields for the beets-filetote plugin."""

import pytest

from tests.pytest_beets_plugin import BeetsPluginFixture


class TestRenameFiletoteFields:
    """Tests to check that Filetote renames using Filetote-provided fields as
    expected for custom path formats.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: BeetsPluginFixture) -> None:
        """Provides shared setup for tests."""
        self.env = beets_plugin_env

        env = self.env
        env.create_flat_import_dir(pair_subfolders=True)
        env.setup_import_session(autotag=False, move=True)

    def test_rename_field_albumpath(self) -> None:
        """Tests that the value of `albumpath` populates in renaming."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/newname"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/newname.file")

    def test_rename_field_old_filename(self) -> None:
        """Tests that the value of `old_filename` populates in renaming."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/$old_filename"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

    def test_rename_field_medianame_old(self) -> None:
        """Tests that the value of `medianame_old` populates in renaming."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file"
        env.config["paths"]["ext:file"] = "$albumpath/$medianame_old"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.file")

    def test_rename_field_medianame_new(self) -> None:
        """Tests that the value of `medianame_new` populates in renaming."""
        env = self.env

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }
        env.config["paths"]["ext:lrc"] = "$albumpath/$medianame_new"

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 3.lrc")

    def test_rename_field_subpath(self) -> None:
        """Tests that the value of `subpath` populates in renaming. Also tests that the
        default lyric file moves as expected without a trailing path separator.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"]["enabled"] = True

        env.config["paths"]["ext:lrc"] = env.fmt_path(
            "$albumpath", "$subpath$medianame_new"
        )

        env.run_cli_command("import")

        env.assert_in_lib_dir(
            "Tag Artist/Tag Album/lyrics/lyric-subfolder/Tag Title 1.lrc"
        )
        env.assert_in_lib_dir(
            "Tag Artist/Tag Album/lyrics/lyric-subfolder/Tag Title 2.lrc"
        )
        env.assert_in_lib_dir(
            "Tag Artist/Tag Album/lyrics/lyric-subfolder/Tag Title 3.lrc"
        )
