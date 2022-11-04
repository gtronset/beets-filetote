import os
import sys

import pytest
from beets import config

from tests.helper import CopyFileArtifactsTestCase, capture_log


class CopyFileArtifactsPrintIgnoredTest(CopyFileArtifactsTestCase):
    """
    Tests to check print ignored files functionality and configuration.
    """

    def setUp(self):
        super(CopyFileArtifactsPrintIgnoredTest, self).setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_do_not_print_ignored_by_default(self):
        config["copyfileartifacts"]["extensions"] = ".file"

        with capture_log() as logs:
            self._run_importer()

        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file2"
        )
        self.assert_not_in_lib_dir(
            b"Tag Artist", b"Tag Album", b"artifact.file3"
        )

        # check output log
        logs = [line for line in logs if line.startswith("copyfileartifacts:")]
        # self.assertEqual(logs, [])

    def test_print_ignored(self):
        config["copyfileartifacts"]["print_ignored"] = True
        config["copyfileartifacts"]["extensions"] = ".file .lrc"

        with capture_log() as logs:
            self._run_importer()

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")

        # check output log
        logs = [line for line in logs if line.startswith("copyfileartifacts:")]
        self.assertEqual(
            logs,
            [
                "copyfileartifacts: Ignored files:",
                "copyfileartifacts:    artifact.nfo",
            ],
        )
