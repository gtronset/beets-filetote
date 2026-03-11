"""Tests multi-disc album import (nested directory structure) for the beets-filetote
plugin.
"""

import pytest

from tests.pytest_beets_plugin import BeetsPluginFixture


class TestMultiDiscImport:
    """Tests that Filetote copies or moves artifact files during multi-disc
    album imports, where songs are organized in subdirectories (e.g., disc1/,
    disc2/).
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: BeetsPluginFixture) -> None:
        """Provides shared setup for tests."""
        self.env = beets_plugin_env

        env = self.env
        env.create_nested_import_dir()
        env.setup_import_session(autotag=False)

    def test_copies_file_from_nested_to_library(self) -> None:
        """Ensures that nested directories are handled by beets and the files
        relocate as expected following the default beets behavior (moves to a
        single directory).
        """
        env = self.env
        env.config["filetote"]["extensions"] = ".file"

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            env.media_count + 4, env.lib_dir / "Tag Artist" / "Tag Album"
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact3.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact4.file")

        env.assert_in_import_dir("the_album/disc1/artifact_disc1.nfo")
        env.assert_in_import_dir("the_album/disc2/artifact_disc2.nfo")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact_disc1.nfo")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact_disc2.lrc")

    def test_copies_file_from_nested_to_nested_library(self) -> None:
        """Ensures that nested directory artifacts are relocated as expected
        when beets is set to use a nested library destination.
        """
        env = self.env
        env.config["filetote"]["extensions"] = ".file"
        env.lib.path_formats = [
            ("default", env.fmt_path("$artist", "$album", "$disc", "$title")),
        ]

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            5, env.lib_dir / "Tag Artist" / "Tag Album" / "01"
        )
        env.assert_number_of_files_in_dir(
            5, env.lib_dir / "Tag Artist" / "Tag Album" / "02"
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/01/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/01/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/02/artifact3.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/02/artifact4.file")

        env.assert_in_import_dir("the_album/disc1/artifact_disc1.nfo")
        env.assert_in_import_dir("the_album/disc2/artifact_disc2.nfo")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/01/artifact_disc1.nfo")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/02/artifact_disc2.lrc")

    @pytest.mark.skip_win32
    def test_copies_file_navigate_in_nested_library(self) -> None:
        """Ensures that nested directory artifacts are relocated using `..` without
        issue. This is skipped in Windows since `..` is taken literally instead of as
        a path component.
        """
        env = self.env
        env.config["filetote"]["extensions"] = ".file"
        env.config["filetote"]["paths"] = {
            "ext:file": env.fmt_path("$albumpath", "..", "artifacts", "$old_filename"),
        }

        env.lib.path_formats = [
            ("default", env.fmt_path("$artist", "$album", "$disc", "$title")),
        ]

        env.run_cli_command("import")

        env.assert_number_of_files_in_dir(
            3, env.lib_dir / "Tag Artist" / "Tag Album" / "01"
        )
        env.assert_number_of_files_in_dir(
            3, env.lib_dir / "Tag Artist" / "Tag Album" / "02"
        )

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifacts/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifacts/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifacts/artifact3.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifacts/artifact4.file")
