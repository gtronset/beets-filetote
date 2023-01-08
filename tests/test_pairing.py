"""Tests pairing the beets-filetote plugin."""

# pylint: disable=missing-function-docstring

import logging
import os

from beets import config

from tests.helper import FiletoteTestCase, MediaSetup

log = logging.getLogger("beets")


class FiletotePairingTest(FiletoteTestCase):
    """
    Tests to check that Filetote handles "pairs" of files.
    """

    def test_pairing_default_is_disabled(self):
        self._create_flat_import_dir(media_files=[MediaSetup(count=1)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_requires_pairing_enabled(self):
        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = False
        config["filetote"]["pairing_only"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_disabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=[MediaSetup(count=1)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = False

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_enabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=[MediaSetup(count=2)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_enabled_works_without_pairs(self):
        self._create_flat_import_dir(
            media_files=[MediaSetup(count=1, generate_pair=False)]
        )
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_does_not_require_pairs_for_all_media(self):
        self._create_flat_import_dir(
            media_files=[MediaSetup(count=2, generate_pair=False)]
        )
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True

        self._create_file(
            os.path.join(self.import_dir, b"the_album"), b"track_1.lrc"
        )

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_disabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=[MediaSetup(count=2)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True
        config["filetote"]["pairing_only"] = False

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_enabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=[MediaSetup(count=2)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True
        config["filetote"]["pairing_only"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_does_not_require_pairs_for_all_media(self):
        self._create_flat_import_dir(
            media_files=[MediaSetup(count=2, generate_pair=False)]
        )
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = True
        config["filetote"]["pairing_only"] = True

        self._create_file(
            os.path.join(self.import_dir, b"the_album"), b"track_1.lrc"
        )

        self._run_importer()

        self.assert_in_import_dir(b"the_album", b"track_1.lrc")
        self.assert_in_import_dir(b"the_album", b"artifact.lrc")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
