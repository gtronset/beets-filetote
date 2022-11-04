import logging
import os
import sys

import pytest
from beets import config

from tests.helper import CopyFileArtifactsTestCase

log = logging.getLogger("beets")


class CopyFileArtifactsPairingTest(CopyFileArtifactsTestCase):
    """
    Tests to check that copyfileartifacts renames as expected for custom path
    formats (both by extension and filename).
    """

    def setUp(self):
        super(CopyFileArtifactsPairingTest, self).setUp()

    def test_pairing_disabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=1)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = False
        config["paths"]["paired-ext:lrc"] = str("$albumpath/$medianame")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_enabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=2)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_only_disabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=2)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = True
        config["copyfileartifacts"]["pairing_only"] = False

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_only_enabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=2)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = True
        config["copyfileartifacts"]["pairing_only"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
