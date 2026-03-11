"""Tests that renaming works as expected when the `convert` plugin is loaded."""

import pytest

from tests.pytest_beets_plugin import BeetsPluginFixture, MediaSetup


class TestConvertPluginRename:
    """Tests that renaming using `item_fields` work as expected when the
    `convert` plugin is loaded.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: BeetsPluginFixture) -> None:
        """All tests in this class load the convert plugin."""
        self.env = beets_plugin_env
        self.env.plugins = ["convert"]

    def test_rename_works_with_convert_plugin(self) -> None:
        """Ensure that Filetote can find artifacts as expected when the `convert`
        plugin is enabled.
        """
        env = self.env

        env.create_flat_import_dir(media_files=[MediaSetup(file_type="wav", count=1)])
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".*"

        temp_convert_dir = env.temp_dir / "temp_convert_dir"
        temp_convert_dir.mkdir(parents=True, exist_ok=True)

        env.config["convert"] = {
            "auto": True,
            "dest": str(env.lib_dir / "Tag Artist" / "Tag Album"),
            "copy_album_art": True,
            "delete_originals": False,
            "format": "flac",
            "never_convert_lossy_files": False,
            "tmpdir": str(temp_convert_dir),
            "quiet": False,
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.flac")
