"""Tests that music files are ignored for the Filetote plugin."""

from mediafile import TYPES as BEETS_TYPES

from tests.pytest_beets_plugin import BeetsEnvFactory, MediaSetup


class TestMusicFilesIgnored:
    """Tests to check that Filetote only copies or moves artifact files and not music
    files as defined by MediaFile's `TYPES` (and Filetote's expanded list).
    """

    def test_default_music_file_types_are_ignored(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that mediafile types are ignored by Filetote."""
        env = beets_flat_env(
            media_files=[
                MediaSetup(file_type=beet_type, count=1) for beet_type in BEETS_TYPES
            ]
        )

        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        for beet_type in BEETS_TYPES:
            env.assert_not_in_lib_dir(f"Tag Artist/Tag Album/track_1.{beet_type}")

    def test_expanded_music_file_types_are_ignored(
        self, beets_flat_env: BeetsEnvFactory
    ) -> None:
        """Ensure that `.m4a`, `.alac.m4a`, `.wma`, and `.wave` file types are ignored
        by Filetote.
        """
        expanded_types = ["m4a", "alac.m4a", "wma", "wave"]

        env = beets_flat_env(
            media_files=[
                MediaSetup(file_type=file_type, count=1) for file_type in expanded_types
            ]
        )

        env.config["filetote"]["extensions"] = ".*"

        env.run_cli_command("import")

        for file_type in expanded_types:
            env.assert_not_in_lib_dir(f"Tag Artist/Tag Album/track_1.{file_type}")
