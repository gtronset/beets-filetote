"""Tests that m4b music/audiobook files are ignored for the beets-filetote
plugin, when the beets-audible plugin is loaded.
"""

import pytest

from tests.pytest_beets_plugin import BeetsPluginFixture, MediaSetup


class TestFiletoteM4BFilesIgnored:
    """Tests to check that Filetote does not copy music/audiobook files when the
    beets-audible plugin is present.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: BeetsPluginFixture) -> None:
        """All tests in this class load the audible stub plugin."""
        self.env = beets_plugin_env
        self.env.plugins = ["audible"]

    def test_expanded_music_file_types_are_ignored(self) -> None:
        """Ensure that `.m4b` file types are ignored by Filetote."""
        env = self.env

        env.create_flat_import_dir(
            media_files=[
                MediaSetup(file_type="mp3", count=1),
                MediaSetup(file_type="m4b", count=1),
            ]
        )
        env.setup_import_session(autotag=False)
        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        env.assert_in_import_dir("the_album/track_1.mp3")
        env.assert_in_import_dir("the_album/track_1.m4b")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.mp3")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.m4b")

        # Filetote should NOT copy m4b as an artifact (source-named)
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/track_1.m4b")
