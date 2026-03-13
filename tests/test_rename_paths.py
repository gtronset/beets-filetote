"""Tests renaming based on paths for the Filetote plugin."""

import pytest

from tests.pytest_beets_plugin import BeetsEnvFactory


class TestRenamePaths:
    """Tests to check that Filetote renames using custom path formats configured either
    in the `paths` section of the overall config or in Filetote's.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Provides shared setup for tests."""
        self.env = beets_flat_env()

    def test_rename_using_filetote_path_when_copying(self) -> None:
        """Tests that renaming works using setting from Filetote's paths."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file .nfo"
        env.config["filetote"]["paths"] = {
            "ext:file": "$albumpath/$artist - $album",
            "ext:nfo": "$albumpath/$artist - $album",
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/Tag Artist - Tag Album.nfo")

    def test_rename_using_filetote_path_pattern_optional(self) -> None:
        """Tests that renaming patterns works using setting from Filetote's paths
        doesn't require `pattern:` prefix.
        """
        env = self.env

        env.config["filetote"]["patterns"] = {
            "file-pattern": ["[Aa]rtifact.file"],
            "nfo-pattern": ["*.nfo"],
        }
        env.config["filetote"]["paths"] = {
            "pattern:file-pattern": "$albumpath/file-pattern $old_filename",
            "nfo-pattern": "$albumpath/nfo-pattern $old_filename",
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/file-pattern artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/nfo-pattern artifact.nfo")

    def test_rename_prioritizes_filetote_path(self) -> None:
        """Tests that Filetote's paths take precedence over beets' global paths."""
        env = self.env

        env.config["filetote"]["patterns"] = {
            "file-pattern": ["[Aa]rtifact.file"],
            "nfo-pattern": ["*.nfo"],
        }
        env.config["paths"] = {
            "pattern:file-pattern": "$albumpath/beets_path $old_filename",
            "nfo-pattern": "$albumpath/beets_path $old_filename",
        }
        env.config["filetote"]["paths"] = {
            "pattern:file-pattern": "$albumpath/filetote_path $old_filename",
            "nfo-pattern": "$albumpath/filetote_path $old_filename",
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/filetote_path artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/filetote_path artifact.nfo")
