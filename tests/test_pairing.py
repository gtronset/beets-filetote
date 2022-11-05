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

    def test_pairing_default_is_disabled(self):
        self._create_flat_import_dir(media_files=1)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_requires_pairing_enabled(self):
        self._create_flat_import_dir(media_files=3)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = False
        config["copyfileartifacts"]["pairing_only"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_disabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=1)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = False

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

    def test_pairing_enabled_works_without_pairs(self):
        self._create_flat_import_dir(media_files=2, generate_pair=False)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_does_not_require_pairs_for_all_media(self):
        self._create_flat_import_dir(media_files=2, generate_pair=False)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = True

        self._create_file(
            os.path.join(self.import_dir, b"the_album"), b"track_1.lrc"
        )

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_disabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=2)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = True
        config["copyfileartifacts"]["pairing_only"] = False

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_enabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=2)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = True
        config["copyfileartifacts"]["pairing_only"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_does_not_require_pairs_for_all_media(self):
        self._create_flat_import_dir(media_files=2, generate_pair=False)
        self._setup_import_session(autotag=False)

        config["copyfileartifacts"]["extensions"] = ".lrc"
        config["copyfileartifacts"]["pairing"] = True
        config["copyfileartifacts"]["pairing_only"] = True

        self._create_file(
            os.path.join(self.import_dir, b"the_album"), b"track_1.lrc"
        )

        self._run_importer()

        self.assert_in_import_dir(b"the_album", b"track_1.lrc")
        self.assert_in_import_dir(b"the_album", b"artifact.lrc")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
