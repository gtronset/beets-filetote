"""Tests to ensure no "could not get filesize" error occurs in the beets-filetote
plugin.
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.pytest_beets_plugin.plugin_fixture import BeetsPluginFixture


class TestNoFilesizeError:
    """Tests to ensure no "could not get filesize" error occurs."""

    @pytest.fixture(autouse=True)
    def _setup(self, beets_plugin_env: "BeetsPluginFixture") -> None:
        """Provides shared setup for tests."""
        self.env = beets_plugin_env

        self.env.create_flat_import_dir()
        self.env.setup_import_session(autotag=False)

    def test_no_filesize_error(self) -> None:
        """Tests to ensure no "could not get filesize" error occurs by confirming no
        warning log is emitted and ensuring the hidden filesize metadata value is
        not `0`.
        """
        env = self.env

        env.config["filetote"]["extensions"] = ".file .lrc"
        env.config["paths"]["ext:file"] = "$albumpath/filesize - ${filesize}b"

        with env.capture_log("beets.filetote") as logs:
            env.run_cli_command("import", operation_option="move")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

        # check output log
        matching_logs = [line for line in logs if "could not get filesize:" in line]
        assert not matching_logs

        env.assert_in_lib_dir("Tag Artist/Tag Album/filesize - 12820b.file")
