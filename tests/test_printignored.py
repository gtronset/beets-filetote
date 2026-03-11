"""Tests print ignored for the beets-filetote plugin."""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.pytest_beets_plugin.plugin_fixture import BeetsPluginFixture


class TestPrintIgnored:
    """Tests to check print ignored files functionality and configuration."""

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: "BeetsPluginFixture") -> None:
        """Provides shared setup for tests."""
        self.env = beets_plugin_env

        env = self.env
        env.create_flat_import_dir()
        env.setup_import_session(autotag=False)

    def test_do_not_print_ignored_by_default(self) -> None:
        """Tests to ensure the default behavior for printing ignored is "disabled"."""
        env = self.env

        env.config["filetote"]["extensions"] = ".file"

        with env.capture_log("beets.filetote") as logs:
            env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")

        assert logs == []

    def test_print_ignored(self) -> None:
        """Tests that when `print_ignored` is enabled, it prints out all files not
        handled by Filetote.
        """
        env = self.env

        env.config["filetote"]["print_ignored"] = True
        env.config["filetote"]["extensions"] = ".file .lrc"

        with env.capture_log("beets.filetote") as logs:
            env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

        assert logs == [
            "filetote: Ignored files:",
            "filetote:    artifact.nfo",
        ]
