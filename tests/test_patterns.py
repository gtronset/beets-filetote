"""Tests "pattern" functionality for the beets-filetote plugin."""

import logging

from typing import TYPE_CHECKING

from beets import config

from tests.helper import FiletoteTestCase, capture_log_with_traceback

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger("beets")


class FiletotePatternTest(FiletoteTestCase):
    """Tests to check that Filetote grabs artfacts by user-definited patterns."""

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_flat_import_dir()
        self._setup_import_session(autotag=False)

    def test_patterns_match_all_glob(self) -> None:
        """Tests that the `*.*` pattern matches all artifacts."""
        config["filetote"]["patterns"] = {
            "all-pattern": ["*.*"],
        }

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")
        self.assert_in_lib_dir("Tag Artist/Tag Album/track_2.lrc")
        self.assert_in_lib_dir("Tag Artist/Tag Album/track_3.lrc")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

    def test_patterns_match(self) -> None:
        """Tests that patterns are used to itentify artifacts."""
        config["filetote"]["patterns"] = {
            "file-pattern": ["[aA]rtifact.file", "artifact[23].file"],
            "nfo-pattern": ["*.nfo"],
        }

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

    def test_patterns_subfolders_match(self) -> None:
        """Tests that patterns can match subdirectories/subfolders."""
        artwork_dir: Path = self.import_dir / "the_album" / "artwork"

        self.create_file(artwork_dir / "cover.jpg")

        config["filetote"]["patterns"] = {
            "file-pattern": ["/[aA]rtifact.file", "artifact[23].file"],
            "subfolder-pattern": ["/[aA]rtwork/cover.jpg"],
        }

        config["paths"]["pattern:subfolder-pattern"] = self.fmt_path(
            "$albumpath", "artwork", "$old_filename"
        )

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artwork/cover.jpg")

    def test_patterns_of_folders_grab_all_files(self) -> None:
        """Tests that patterns of just folders grab all contents."""
        artwork_dir: Path = self.import_dir / "the_album" / "artwork"
        cd1_dir: Path = self.import_dir / "the_album" / "CD1"
        subfolder_dir: Path = (
            self.import_dir / "the_album" / "Subfolder1" / "Subfolder2" / "Subfolder3"
        )

        self.create_file(artwork_dir / "cover.jpg")
        self.create_file(cd1_dir / "cd.file")
        self.create_file(subfolder_dir / "sub.file")

        config["filetote"]["patterns"] = {
            "subfolder1-pattern": ["[aA]rtwork/"],
            "subfolder2-pattern": ["CD1/*.*"],
            "subfolder3-pattern": ["Subfolder1/Subfolder2/"],
        }

        config["paths"]["pattern:subfolder1-pattern"] = self.fmt_path(
            "$albumpath", "artwork", "$old_filename"
        )

        config["paths"]["pattern:subfolder3-pattern"] = self.fmt_path(
            "$albumpath", "sub1", "sub2", "$old_filename"
        )

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/artwork/cover.jpg")
        self.assert_in_lib_dir("Tag Artist/Tag Album/cd.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/sub1/sub2/sub.file")

    def test_patterns_path_sep_normalization(self) -> None:
        r"""Tests that path separators in patterns can work for both *Nix/macOS (/)
        and Windows (\\).
        """
        artwork_dir: Path = self.import_dir / "the_album" / "artwork"
        scans_dir: Path = self.import_dir / "the_album" / "scans"

        self.create_file(artwork_dir / "cover.jpg")
        self.create_file(scans_dir / "scan.jpg")

        config["filetote"]["patterns"] = {
            "artwork-pattern": ["[aA]rtwork/"],
            "scans-pattern": ["[sS]cans\\"],
        }

        config["paths"]["pattern:artwork-pattern"] = self.fmt_path(
            "$albumpath", "artwork", "$old_filename"
        )

        config["paths"]["pattern:scans-pattern"] = self.fmt_path(
            "$albumpath", "scans", "$old_filename"
        )

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/artwork/cover.jpg")
        self.assert_in_lib_dir("Tag Artist/Tag Album/scans/scan.jpg")

    def test_patterns_path_renaming(self) -> None:
        """Tests that the path definition for `pattern:` prefix works."""
        config["filetote"]["patterns"] = {
            "file-pattern": ["[Aa]rtifact.file", "artifact[23].file"],
            "nfo-pattern": ["*.nfo"],
        }
        config["paths"]["pattern:file-pattern"] = (
            "$albumpath/file-pattern $old_filename"
        )

        config["paths"]["pattern:nfo-pattern"] = "$albumpath/nfo-pattern $old_filename"

        with capture_log_with_traceback() as logs:
            self._run_cli_command("import")

        for line in logs:
            if line.startswith("filetote:"):
                log.info(line)

        self.assert_in_lib_dir("Tag Artist/Tag Album/file-pattern artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/file-pattern artifact2.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/nfo-pattern artifact.nfo")
