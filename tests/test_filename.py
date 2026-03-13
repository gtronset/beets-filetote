"""Tests file-naming for the Filetote plugin."""

import re

import pytest

from tests.pytest_beets_plugin import BeetsEnvFactory


class TestFilename:
    """Tests to check handling of artifacts with filenames containing unicode
    characters.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Provides shared setup for tests."""
        self.env = beets_flat_env(move=True)

        self.env.config["filetote"]["extensions"] = ".file"

    def test_import_dir_with_unicode_character_in_artifact_name_copy(self) -> None:
        """Tests that unicode characters copy as expected."""
        env = self.env

        env.config["import"]["move"] = False
        env.config["import"]["copy"] = True

        env.create_simple_import_dir(artifacts=["\xe4rtifact.file"])

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/\xe4rtifact.file")

    def test_import_dir_with_unicode_character_in_artifact_name_move(self) -> None:
        """Tests that unicode characters move as expected."""
        env = self.env

        env.create_simple_import_dir(artifacts=["\xe4rtifact.file"])

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/\xe4rtifact.file")

    @pytest.mark.skip_win32
    def test_import_with_illegal_character_in_artifact_name_obeys_beets(
        self,
    ) -> None:
        """Tests that illegal characters in file name are replaced following beets
        conventions. This is skipped in Windows as the characters used here are not
        allowed.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".log"
        env.config["paths"]["ext:.log"] = "$albumpath/$album - $old_filename"

        env.lib.path_formats[0] = (
            "default",
            env.fmt_path("$artist", "$album", "$album - $title"),
        )

        env.create_simple_import_dir(artifacts=["CoolName: Album&Tag.log"])

        env.update_medium(
            env.import_dir / "the_album" / "track_1.mp3",
            {"album": "Album: Subtitle"},
        )

        env.run_cli_command("import")

        env.assert_in_lib_dir(
            "Tag Artist/Album_ Subtitle/Album_ Subtitle - CoolName_ Album&Tag.log"
        )

    def test_import_dir_with_illegal_character_in_album_name(self) -> None:
        """Tests that illegal characters in album name are replaced following beets
        conventions.
        """
        env = self.env

        env.config["paths"]["ext:file"] = "$albumpath/$artist - $album"

        env.create_simple_import_dir(artifacts=["artifact.file"])

        env.update_medium(
            env.import_dir / "the_album" / "track_1.mp3",
            {"album": "Tag Album?"},
        )

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album_/Tag Artist - Tag Album_.file")

    def test_rename_works_with_custom_replace(self) -> None:
        """Tests that custom "replace" settings work as expected."""
        env = self.env
        env.config["paths"]["ext:file"] = "$albumpath/$title"
        env.config["replace"][r"\?"] = "\uff1f"

        env.lib.replacements = [
            (re.compile(r"\:"), "_"),
            (re.compile(r"\?"), "\uff1f"),
        ]

        env.create_simple_import_dir(artifacts=["artifact.file"])

        env.update_medium(
            env.import_dir / "the_album" / "track_1.mp3",
            {"title": "Tag: Title?"},
        )

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag_ Title\uff1f.file")
