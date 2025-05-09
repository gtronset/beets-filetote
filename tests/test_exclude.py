"""Tests to ensure no "could not get filesize" error occurs in the beets-filetote
plugin.
"""

import os

from typing import List, Optional

import beets

from beets import config

from tests.helper import FiletoteTestCase, capture_log


class FiletoteExcludeTest(FiletoteTestCase):
    """Tests to ensure no "could not get filesize" error occurs."""

    def setUp(self, _other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()

        self.album_path = os.path.join(self.import_dir, b"the_album")

        self._setup_import_session(move=True, autotag=False)

    def test_exclude_strseq_of_filenames(self) -> None:
        """Tests to ensure the `exclude` config registers as a strseq (string
        sequence) of filenames.
        """
        config["filetote"]["extensions"] = ".file .lrc"
        config["filetote"]["exclude"] = "nottobemoved.file nottobemoved.lrc"
        config["paths"]["ext:file"] = "$albumpath/$old_filename"

        self.create_file(
            self.album_path, beets.util.bytestring_path("nottobemoved.file")
        )

        self.create_file(
            self.album_path, beets.util.bytestring_path("nottobemoved.lrc")
        )

        with capture_log() as logs:
            self._run_cli_command("import")

        self.assert_in_import_dir(
            b"the_album",
            b"nottobemoved.file",
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"nottobemoved.file")

        self.assert_in_import_dir(
            b"the_album",
            b"nottobemoved.lrc",
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"nottobemoved.lrc")

        # Ensure the deprecation warning is present
        logs = [line for line in logs if line.startswith("filetote:")]
        assert logs == [
            (
                "filetote: Depreaction warning: The `exclude` plugin should now use the"
                " explicit settings of `filenames`, `extensions`, and/or `patterns`."
                " See the `exclude` documentation for more details:"
                " https://github.com/gtronset/beets-filetote#excluding-files"
            )
        ]

    def test_exclude_dict_with_filenames_extensions(self) -> None:
        """Tests to ensure the `exclude` config registers dictionary of `filenames`
        and/or `extensions`.
        """
        config["filetote"]["extensions"] = ".*"

        config["filetote"]["exclude"] = {
            "filenames": ["nottobemoved.file"],
            "extensions": [".lrc"],
        }

        self.create_file(
            self.album_path, beets.util.bytestring_path("nottobemoved.file")
        )

        self.create_file(
            self.album_path, beets.util.bytestring_path("nottobemoved.lrc")
        )

        self._run_cli_command("import")

        self.assert_in_import_dir(
            b"the_album",
            b"nottobemoved.file",
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"nottobemoved.file")

        self.assert_in_import_dir(
            b"the_album",
            b"nottobemoved.lrc",
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"nottobemoved.lrc")

    def test_exclude_dict_with_patterns(self) -> None:
        """Tests to ensure the `exclude` config registers as a strseg (string
        sequence) of filenames.
        """
        config["filetote"]["extensions"] = ".*"

        config["filetote"]["exclude"]["patterns"] = {
            "file-pattern": ["[aA]rtifact.*"],
            "nfo-pattern": ["*.lrc"],
        }

        self.create_file(self.album_path, beets.util.bytestring_path("tobemoved.file"))

        self.create_file(
            self.album_path, beets.util.bytestring_path("nottobemoved.lrc")
        )

        self._run_cli_command("import")

        self.assert_in_lib_dir(
            b"Tag Artist",
            b"Tag Album",
            b"tobemoved.file",
        )
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"nottobemoved.lrc")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
