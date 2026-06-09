"""Tests that renaming using `item_fields` work as expected when the `inline` plugin is
loaded.
"""

from tests.pytest_beets_plugin import BeetsEnvFactory


class TestInlinePluginRename:
    """Tests that renaming using `item_fields` work as expected when the `inline` plugin
    is loaded.
    """

    def test_rename_works_with_inline_plugin(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that Filetote can rename fields as expected when the `inline` plugin
        is enabled.
        """
        env = beets_flat_env()

        env.plugins = ["inline"]

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
