"""Tests to ensure no "could not get filesize" error occurs in the beets-filetote
plugin.
"""

import os

from typing import List, Optional

import beets

from beets import config

from tests.helper import FiletoteTestCase


class FiletoteExcludeTest(FiletoteTestCase):
    """Tests to ensure no "could not get filesize" error occurs."""

    def setUp(self, _other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()

        self.album_path = os.path.join(self.import_dir, b"the_album")

        self._setup_import_session(autotag=False)

    def test_exclude_strseq_of_filenames(self) -> None:
        """Tests to ensure the `exclude` config registers as a strseg (string
        sequence) of filenames.
        """
        config["filetote"]["extensions"] = ".file .lrc"
        config["filetote"]["exclude"] = "nottobecopied.file nottobecopied.lrc"
        config["paths"]["ext:file"] = "$albumpath/$old_filename"

        self.create_file(
            self.album_path, beets.util.bytestring_path("nottobecopied.file")
        )

        self.create_file(
            self.album_path, beets.util.bytestring_path("nottobecopied.lrc")
        )

        self._run_cli_command("import")

        self.assert_in_import_dir(
            b"the_album",
            b"nottobecopied.file",
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"nottobecopied.file")

        self.assert_in_import_dir(
            b"the_album",
            b"nottobecopied.lrc",
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"nottobecopied.lrc")

    def test_exclude_dict_of_options(self) -> None:
        """Tests to ensure the `exclude` config registers as a strseg (string
        sequence) of filenames.
        """
        config["filetote"]["extensions"] = ".*"
        config["paths"]["ext:.*"] = "$albumpath/$artist - $old_filename"

        config["filetote"]["exclude"] = {
            "filenames": ["nottobecopied.file"],
            "extensions": [".lrc"],
        }

        self.create_file(
            self.album_path, beets.util.bytestring_path("nottobecopied.file")
        )

        self.create_file(
            self.album_path, beets.util.bytestring_path("nottobecopied.lrc")
        )

        self._run_cli_command("import")

        self.assert_in_import_dir(
            b"the_album",
            b"nottobecopied.file",
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"nottobecopied.file")

        self.assert_in_import_dir(
            b"the_album",
            b"nottobecopied.lrc",
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"nottobecopied.lrc")
