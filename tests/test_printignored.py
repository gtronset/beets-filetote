"""Tests print ignored for the beets-filetote plugin."""

from typing import Optional

from beets import config

from tests.helper import FiletoteTestCase, capture_log_with_traceback


class FiletotePrintIgnoredTest(FiletoteTestCase):
    """Tests to check print ignored files functionality and configuration."""

    def setUp(self, _other_plugins: Optional[list[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_do_not_print_ignored_by_default(self) -> None:
        """Tests to ensure the default behavior for printing ignored is "disabled"."""
        config["filetote"]["extensions"] = ".file"

        with capture_log_with_traceback() as logs:
            self._run_cli_command("import")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

        # check output log
        logs = [line for line in logs if line.startswith("filetote:")]
        assert logs == []

    def test_print_ignored(self) -> None:
        """Tests that when `print_ignored` is enabled, it prints out all files not
        handled by Filetote.
        """
        config["filetote"]["print_ignored"] = True
        config["filetote"]["extensions"] = ".file .lrc"

        with capture_log_with_traceback() as logs:
            self._run_cli_command("import")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")

        # check output log
        logs = [line for line in logs if line.startswith("filetote:")]
        assert logs == [
            "filetote: Ignored files:",
            "filetote:    artifact.nfo",
        ]
