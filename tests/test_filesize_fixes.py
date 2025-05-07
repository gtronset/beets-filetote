"""Tests to ensure no "could not get filesize" error occurs in the beets-filetote
plugin.
"""

from typing import List, Optional

from beets import config

from tests.helper import FiletoteTestCase, capture_log


class FiletoteNoFilesizeErrorTest(FiletoteTestCase):
    """Tests to ensure no "could not get filesize" error occurs."""

    def setUp(self, _other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_no_filesize_error(self) -> None:
        """Tests to ensure no "could not get filesize" error occurs by confirming no
        warning log is emitted and ensuring the hidden filesize metadata value is
        not `0`.
        """
        config["filetote"]["extensions"] = ".file .lrc"
        config["paths"]["ext:file"] = "$albumpath/filesize - ${filesize}b"

        with capture_log() as logs:
            self._run_cli_command("import", operation_option="move")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")

        # check output log
        matching_logs = [
            line for line in logs if line.startswith("could not get filesize:")
        ]
        assert not matching_logs

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"filesize - 12820b.file",
        )
