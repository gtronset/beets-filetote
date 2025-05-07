"""Tests that music files are ignored for the beets-filetote plugin."""

import logging

from beets import config
from mediafile import TYPES as BEETS_TYPES

from tests.helper import FiletoteTestCase, MediaSetup

log = logging.getLogger("beets")


class FiletoteMusicFilesIgnoredTest(FiletoteTestCase):
    """Tests to check that Filetote only copies or moves artifact files and not
    music files as defined by MediaFile's TYPES and expanded list.
    """

    def test_default_music_file_types_are_ignored(self) -> None:
        """Ensure that mediafile types are ignored by Filetote."""
        media_file_list = []

        for beet_type in BEETS_TYPES:
            media_file_list.append(MediaSetup(file_type=beet_type, count=1))

        self._create_flat_import_dir(media_files=media_file_list)
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".*"

        self._run_cli_command("import")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.aac")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.aiff")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.alac")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.ape")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.asf")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.dsf")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.flac")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.mp3")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.mpc")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.ogg")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.opus")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.wav")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.wv")

    def test_expanded_music_file_types_are_ignored(self) -> None:
        """Ensure that `.m4a`, `.alac.m4a`, `.wma`, and `.wave` file types are
        ignored by Filetote.
        """
        media_file_list = [
            MediaSetup(file_type="m4a", count=1),
            MediaSetup(file_type="alac.m4a", count=1),
            MediaSetup(file_type="wma", count=1),
            MediaSetup(file_type="wave", count=1),
        ]

        self._create_flat_import_dir(media_files=media_file_list)
        self._setup_import_session(autotag=False)

        config["filetote"]["extensions"] = ".*"

        self._run_cli_command("import")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.m4a")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.alac.m4a")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.wma")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"track_1.wave")
