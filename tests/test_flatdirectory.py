"""Tests flat directory structure for the beets-filetote plugin."""

import logging
import os

from typing import List, Optional

from beets import config

from tests.helper import FiletoteTestCase

log = logging.getLogger("beets")


class FiletoteFromFlatDirectoryTest(FiletoteTestCase):
    """Tests to check that Filetote copies or moves artifact files from a
    flat directory (e.g., all songs in an album are imported from a single
    directory). Also tests `extensions` and `filenames` config options.
    """

    def setUp(self, _other_plugins: Optional[List[str]] = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

        self._base_file_count = self._media_count + self._pairs_count

    def test_only_copies_files_matching_configured_extension(self) -> None:
        """Test that Filetote only copies files by specific extension when set."""
        config["filetote"]["extensions"] = ".file"

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            self._media_count + 2, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

        self.assert_in_import_dir(b"the_album", b"artifact.nfo")
        self.assert_in_import_dir(b"the_album", b"artifact.lrc")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_exact_matching_configured_extension(self) -> None:
        """Test that extensions and other fields matching are exact, not just
        partial matches.
        """
        config["filetote"]["extensions"] = ".file"

        self.create_file(os.path.join(self.import_dir, b"the_album"), b"artifact.file2")

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            self._media_count + 2, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")

        self.assert_in_import_dir(b"the_album", b"artifact.file2")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file2")

    def test_exclude_artifacts_matching_configured_exclude(self) -> None:
        """Test that specified excludes are not moved/copied."""
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["exclude"] = "artifact2.file"

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            self._media_count + 1, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_only_copy_artifacts_matching_configured_filename(self) -> None:
        """Test that only the specific file (by filename) is copied when specified."""
        config["filetote"]["filenames"] = "artifact.file"

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            self._media_count + 1, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_only_copy_artifacts_matching_configured_extension_and_filename(
        self,
    ) -> None:
        """Test that multiple definitions work and the all matches copy."""
        config["filetote"]["extensions"] = ".file"
        config["filetote"]["filenames"] = "artifact.nfo"

        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            self._media_count + 3, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")

    def test_copy_no_artifacts_by_default(self) -> None:
        """Ensure that all artifacts that match the extensions are moved by default."""
        self._run_cli_command("import")

        self.assert_number_of_files_in_dir(
            self._media_count, self.lib_dir, b"Tag Artist", b"Tag Album"
        )

        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact2.file")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.nfo")
        self.assert_not_in_lib_dir(b"Tag Artist", b"Tag Album", b"artifact.lrc")
