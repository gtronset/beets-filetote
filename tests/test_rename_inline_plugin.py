"""Tests that renaming using `item_fields` work as expected when the
`inline` plugin is loaded.
"""

import pytest

from tests.pytest_beets_plugin import BeetsPluginFixture


class TestInlinePluginRename:
    """Tests that renaming using `item_fields` work as expected when the
    `inline` plugin is loaded.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: BeetsPluginFixture) -> None:
        """All tests in this class load the inline plugin."""
        self.env = beets_plugin_env
        self.env.plugins = ["inline"]

    def test_rename_works_with_inline_plugin(self) -> None:
        """Ensure that Filetote can rename fields as expected when the `inline`
        plugin is enabled.
        """
        env = self.env

        env.create_flat_import_dir()
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".*"
        env.config["filetote"]["patterns"] = {
            "file-pattern": ["*.file"],
        }
        env.config["paths"]["ext:file"] = (
            "$albumpath/%if{$multidisc,Disc $disc} - $old_filename"
        )

        env.config["item_fields"]["multidisc"] = "1 if disctotal > 1 else 0"

        env.lib.path_formats[0] = (
            "default",
            env.fmt_path("$artist", "$album", "%if{$multidisc,Disc $disc/}$title"),
        )

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Disc 01/Disc 01 - artifact.file")
