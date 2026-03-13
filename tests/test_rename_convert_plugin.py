"""Tests that renaming works as expected when the `convert` plugin is loaded."""

from tests.pytest_beets_plugin import MediaSetup
from tests.pytest_beets_plugin.fixtures import BeetsEnvFactory


class TestConvertPluginRename:
    """Tests that renaming using `item_fields` work as expected when the
    `convert` plugin is loaded.
    """

    def test_rename_works_with_convert_plugin(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that Filetote can find artifacts as expected when the `convert`
        plugin is enabled.
        """
        env = beets_flat_env(media_files=[MediaSetup(file_type="wav", count=1)])

        env.plugins = ["convert"]

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
