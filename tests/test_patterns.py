"""Tests "pattern" functionality for the Filetote plugin."""

import pytest

from tests.pytest_beets_plugin import BeetsEnvFactory


class TestPatterns:
    """Tests to check that Filetote grabs artifacts by user-defined patterns."""

    @pytest.fixture(autouse=True)
    def _setup(self, beets_flat_env: BeetsEnvFactory) -> None:
        """Provides shared setup for tests."""
        self.env = beets_flat_env()

    def test_patterns_match_all_glob(self) -> None:
        """Tests that the `*.*` pattern matches all artifacts."""
        env = self.env

        env.config["filetote"]["patterns"] = {
            "all-pattern": ["*.*"],
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/track_1.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/track_2.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/track_3.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.lrc")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

    def test_patterns_match(self) -> None:
        """Tests that patterns are used to identify artifacts."""
        env = self.env

        env.config["filetote"]["patterns"] = {
            "file-pattern": ["[aA]rtifact.file", "artifact[23].file"],
            "nfo-pattern": ["*.nfo"],
        }

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

    def test_patterns_subfolders_match(self) -> None:
        """Tests that patterns can match subdirectories/subfolders."""
        env = self.env
        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "artwork" / "cover.jpg")

        env.config["filetote"]["patterns"] = {
            "file-pattern": ["/[aA]rtifact.file", "artifact[23].file"],
            "subfolder-pattern": ["/[aA]rtwork/cover.jpg"],
        }

        env.config["paths"]["pattern:subfolder-pattern"] = env.fmt_path(
            "$albumpath", "artwork", "$old_filename"
        )

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artwork/cover.jpg")

    def test_patterns_of_folders_grab_all_files(self) -> None:
        """Tests that patterns of just folders grab all contents."""
        env = self.env
        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "artwork" / "cover.jpg")
        env.create_file(album_path / "CD1" / "cd.file")
        env.create_file(
            album_path / "Subfolder1" / "Subfolder2" / "Subfolder3" / "sub.file"
        )

        env.config["filetote"]["patterns"] = {
            "subfolder1-pattern": ["[aA]rtwork/"],
            "subfolder2-pattern": ["CD1/*.*"],
            "subfolder3-pattern": ["Subfolder1/Subfolder2/"],
        }

        env.config["paths"]["pattern:subfolder1-pattern"] = env.fmt_path(
            "$albumpath", "artwork", "$old_filename"
        )

        env.config["paths"]["pattern:subfolder3-pattern"] = env.fmt_path(
            "$albumpath", "sub1", "sub2", "$old_filename"
        )

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artwork/cover.jpg")
        env.assert_in_lib_dir("Tag Artist/Tag Album/cd.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/sub1/sub2/sub.file")

    def test_patterns_path_sep_normalization(self) -> None:
        r"""Tests that path separators in patterns can work for both Unix-like/macOS
        (`/`) and Windows (`\\`).
        """
        env = self.env
        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "artwork" / "cover.jpg")
        env.create_file(album_path / "scans" / "scan.jpg")

        env.config["filetote"]["patterns"] = {
            "artwork-pattern": ["[aA]rtwork/"],
            "scans-pattern": ["[sS]cans\\"],
        }

        env.config["paths"]["pattern:artwork-pattern"] = env.fmt_path(
            "$albumpath", "artwork", "$old_filename"
        )

        env.config["paths"]["pattern:scans-pattern"] = env.fmt_path(
            "$albumpath", "scans", "$old_filename"
        )

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artwork/cover.jpg")
        env.assert_in_lib_dir("Tag Artist/Tag Album/scans/scan.jpg")

    def test_patterns_path_renaming(self) -> None:
        """Tests that the path definition for `pattern:` prefix works."""
        env = self.env

        env.config["filetote"]["patterns"] = {
            "file-pattern": ["[Aa]rtifact.file", "artifact[23].file"],
            "nfo-pattern": ["*.nfo"],
        }

        env.config["paths"]["pattern:file-pattern"] = (
            "$albumpath/file-pattern $old_filename"
        )
        env.config["paths"]["pattern:nfo-pattern"] = (
            "$albumpath/nfo-pattern $old_filename"
        )

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/file-pattern artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/file-pattern artifact2.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/nfo-pattern artifact.nfo")
