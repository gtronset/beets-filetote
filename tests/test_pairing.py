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
        config["filetote"]["pairing"] = {
            "enabled": False,
            "pairing_only": True,
        }

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_disabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=[MediaSetup(count=1)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"]["enabled"] = False

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_enabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=[MediaSetup(count=2)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"]["enabled"] = True

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
        config["filetote"]["pairing"]["enabled"] = True

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_does_not_require_pairs_for_all_media(self):
        self._create_flat_import_dir(
            media_files=[MediaSetup(count=2, generate_pair=False)]
        )
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"]["enabled"] = True

        self._create_file(os.path.join(self.import_dir, b"the_album"), b"track_1.lrc")

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_disabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=[MediaSetup(count=2)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": False,
        }

        self._run_importer()

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_2.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairingonly_enabled_copies_all_matches(self):
        self._create_flat_import_dir(media_files=[MediaSetup(count=2)])
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }

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
        config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }

        self._create_file(os.path.join(self.import_dir, b"the_album"), b"track_1.lrc")

        self._run_importer()

        self.assert_in_import_dir(b"the_album", b"track_1.lrc")
        self.assert_in_import_dir(b"the_album", b"artifact.lrc")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_extensions(self):
        self._create_flat_import_dir(
            media_files=[MediaSetup(count=2, generate_pair=False)]
        )
        self._setup_import_session(autotag=False)

        config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
            "extensions": ".lrc .kar",
        }

        new_files = [b"track_1.kar", b"track_1.lrc", b"track_1.jpg"]

        for filename in new_files:
            self._create_file(os.path.join(self.import_dir, b"the_album"), filename)

        self._run_importer()

        self.assert_in_import_dir(b"the_album", b"track_1.lrc")
        self.assert_in_import_dir(b"the_album", b"artifact.lrc")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.kar")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.jpg")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_pairing_extensions_are_addative_to_toplevel_extensions(self):
        self._create_flat_import_dir(
            media_files=[MediaSetup(count=2, generate_pair=False)]
        )
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".jpg"

        config["filetote"]["pairing"] = {
            "enabled": True,
            "extensions": ".lrc",
        }

        new_files = [b"track_1.kar", b"track_1.lrc", b"track_1.jpg"]

        for filename in new_files:
            self._create_file(os.path.join(self.import_dir, b"the_album"), filename)

        self._run_importer()

        self.assert_in_import_dir(b"the_album", b"track_1.lrc")
        self.assert_in_import_dir(b"the_album", b"artifact.lrc")

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.lrc")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.jpg")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.kar")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
