"""Tests that music files are ignored for the beets-filetote plugin."""

from typing import TYPE_CHECKING

import pytest

from mediafile import TYPES as BEETS_TYPES

from tests.pytest_beets_plugin import MediaSetup

if TYPE_CHECKING:
    from tests.pytest_beets_plugin.plugin_fixture import BeetsPluginFixture


class TestMusicFilesIgnored:
    """Tests to check that Filetote only copies or moves artifact files and not
    music files as defined by MediaFile's TYPES and expanded list.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: "BeetsPluginFixture") -> None:
        """Provides shared setup for tests."""
        self.env = beets_plugin_env

    def test_default_music_file_types_are_ignored(self) -> None:
        """Ensure that mediafile types are ignored by Filetote."""
        env = self.env

        media_file_list = [
            MediaSetup(file_type=beet_type, count=1) for beet_type in BEETS_TYPES
        ]

        env.create_flat_import_dir(media_files=media_file_list)
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        for beet_type in BEETS_TYPES:
            env.assert_not_in_lib_dir(f"Tag Artist/Tag Album/track_1.{beet_type}")

    def test_expanded_music_file_types_are_ignored(self) -> None:
        """Ensure that `.m4a`, `.alac.m4a`, `.wma`, and `.wave` file types are
        ignored by Filetote.
        """
        env = self.env

        expanded_types = ["m4a", "alac.m4a", "wma", "wave"]

        media_file_list = [
            MediaSetup(file_type=file_type, count=1) for file_type in expanded_types
        ]

        env.create_flat_import_dir(media_files=media_file_list)
        env.setup_import_session(autotag=False)

        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        for file_type in expanded_types:
            env.assert_not_in_lib_dir(f"Tag Artist/Tag Album/track_1.{file_type}")
