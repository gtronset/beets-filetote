"""Tests to ensure no "could not get filesize" error occurs in the beets-filetote
plugin.
"""

from tests.pytest_beets_plugin import BeetsEnvFactory


class TestNoFilesizeError:
    """Tests to ensure no "could not get filesize" error occurs."""

    def test_no_filesize_error(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Tests to ensure no "could not get filesize" error occurs by confirming no
        warning log is emitted and ensuring the hidden filesize metadata value is
        not `0`.
        """
        env = beets_flat_env()

        env.config["filetote"]["extensions"] = ".file .lrc"
        env.config["paths"]["ext:file"] = "$albumpath/filesize - ${filesize}b"

        with env.capture_log("beets.filetote") as logs:
            env.run_cli_command("import", operation_option="move")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

        # check output log
        matching_logs = [line for line in logs if "could not get filesize:" in line]
        assert not matching_logs

        env.assert_in_lib_dir("Tag Artist/Tag Album/filesize - 12820b.file")
