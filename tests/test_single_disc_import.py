"""Tests single-disc album import (flat directory structure) for the Filetote
plugin.
"""

import pytest

from tests.pytest_beets_plugin import BeetsEnvFactory


class TestFromFlatDirectory:
    """Tests that Filetote copies or moves artifact files during single-disc album
    imports. Also tests `extensions` and `filenames` config options.
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Provides shared setup for tests."""
        self.env = beets_flat_env()

    def test_only_copies_files_matching_configured_extension(self) -> None:
        """Test that Filetote only copies files by specific extension when set."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file"

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count + 2, env.lib_dir / "Tag Artist" / "Tag Album"
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

        env.assert_in_import_dir("the_album/artifact.nfo")
        env.assert_in_import_dir("the_album/artifact.lrc")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_exact_matching_configured_extension(self) -> None:
        """Test that extensions and other fields matching are exact, not just partial
        matches.
        """
        env = self.env
        env.config["filetote"]["extensions"] = ".file"

        env.create_file(env.import_dir / "the_album" / "artifact.file2")

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count + 2, env.lib_dir / "Tag Artist" / "Tag Album"
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

        env.assert_in_import_dir("the_album/artifact.file2")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file2")

    def test_exclude_artifacts_matching_configured_exclude(self) -> None:
        """Test that specified excludes are not moved/copied."""
        env = self.env
        env.config["filetote"]["extensions"] = ".file"
        env.config["filetote"]["exclude"] = "artifact2.file"

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count + 1, env.lib_dir / "Tag Artist" / "Tag Album"
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_only_copy_artifacts_matching_configured_filename(self) -> None:
        """Test that only the specific file (by filename) is copied when specified."""
        env = self.env
        env.config["filetote"]["filenames"] = "artifact.file"

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count + 1, env.lib_dir / "Tag Artist" / "Tag Album"
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_only_copy_artifacts_matching_configured_extension_and_filename(
        self,
    ) -> None:
        """Test that multiple definitions work and the all matches copy."""
        env = self.env
        env.config["filetote"]["extensions"] = ".file"
        env.config["filetote"]["filenames"] = "artifact.nfo"

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count + 3, env.lib_dir / "Tag Artist" / "Tag Album"
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_copy_no_artifacts_by_default(self) -> None:
        """Ensure that no artifacts are copied by default (i.e., Filetote needs to be
        configured).
        """
        env = self.env
        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count, env.lib_dir / "Tag Artist" / "Tag Album"
        )

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

    def test_shared_artifacts_handled_once_for_multi_item_album(self) -> None:
        """Tests that shared artifacts in a directory with multiple media files are
        handled correctly and only once.
        """
        env = self.env
        env.config["filetote"]["extensions"] = [".nfo", ".file"]

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count + 3, env.lib_dir / "Tag Artist" / "Tag Album"
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")
