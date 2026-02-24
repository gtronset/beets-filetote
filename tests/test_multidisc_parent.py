"""Tests for handling artifacts in parent directories of multi-disc albums."""

from beets import config

from tests.helper import FiletoteTestCase


class FiletoteMultidiscParentTest(FiletoteTestCase):
    """Tests that Filetote correctly handles artifacts located in the parent
    directory of a multi-disc album (e.g., Album/summary.txt alongside
    Album/Disc1/).
    """

    def setUp(self, _other_plugins: list[str] | None = None) -> None:
        """Provides shared setup for tests."""
        super().setUp()

        self._create_nested_import_dir()

        self.album_path = self.import_dir / "the_album"

        self.create_file(self.album_path / "summary.txt")
        self.create_file(self.album_path / "artifact.nfo")

        (self.album_path / "artwork").mkdir()
        self.create_file(self.album_path / "artwork" / "poster.jpg")

        self._setup_import_session(autotag=False)

    def test_collects_parent_artifacts(self) -> None:
        """Ensures artifacts in the parent album directory are collected and
        moved to the destination library, alongside the disc contents.
        """
        config["filetote"]["extensions"] = [".file", ".txt", ".nfo", ".jpg"]

        self._run_cli_command("import")

        # Verify standard disc-level artifacts moved (baseline check)
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

        # Verify Parent artifacts were moved
        self.assert_in_lib_dir("Tag Artist/Tag Album/summary.txt")
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

        # Verify Parent subdirectory artifacts were moved
        self.assert_in_lib_dir("Tag Artist/Tag Album/poster.jpg")

    def test_collects_parent_artifacts_into_disc_paths(self) -> None:
        """Ensures that if the user has a nested library path (Album/Disc 01/),
        the parent artifacts are effectively copied/moved relative to the items.

        Ensure that artifacts in the Parent are only processed once.
        """
        config["filetote"]["extensions"] = [".file", ".txt"]

        # Use disc folders: Artist/Album/01/Title.mp3
        self.lib.path_formats = [
            ("default", self.fmt_path("$artist", "$album", "$disc", "$title")),
        ]

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/01/artifact.file")

        # `summary.txt` in the Parent should only be processed once, as part of Disc 01.
        self.assert_in_lib_dir("Tag Artist/Tag Album/01/summary.txt")
        self.assert_not_in_lib_dir("Tag Artist/Tag Album/02/summary.txt")

    def test_ignores_sibling_disc_folders(self) -> None:
        """Verify that when processing artifacts for Disc 1, artifacts from Disc 2
        (sibling folder) are not grabbed while scanning the parent.
        """
        config["filetote"]["extensions"] = ".file"

        # Use disc foldersto verify artifacts stay with their own disc.
        self.lib.path_formats = [
            ("default", self.fmt_path("$artist", "$album", "$disc", "$title")),
        ]

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/01/artifact.file")
        self.assert_not_in_lib_dir("Tag Artist/Tag Album/02/artifact.file")

        self.assert_in_lib_dir("Tag Artist/Tag Album/02/artifact3.file")
        self.assert_not_in_lib_dir("Tag Artist/Tag Album/01/artifact3.file")

    def test_preserves_parent_structure_with_pattern(self) -> None:
        """Verify that original structure for Parent artifacts can be recreated."""
        config["filetote"]["extensions"] = ".jpg"
        config["filetote"]["paths"] = {
            "pattern:artwork": "$albumpath/artwork/$old_filename"
        }
        config["filetote"]["patterns"] = {"artwork": ["artwork/*.jpg"]}

        self._run_cli_command("import")

        self.assert_in_lib_dir("Tag Artist/Tag Album/artwork/poster.jpg")

    def test_parent_artifacts_do_not_pair_with_subdirectory_tracks(self) -> None:
        """Verify that an artifact in the Parent folder ("Aunt") does NOT pair
        with a track in a Subdirectory ("Niece"), even if names match.
        Example: `Album/01.lrc` should NOT pair with `Album/CD1/01.mp3`.
        """
        config["filetote"]["extensions"] = ".lrc"
        config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }

        self.create_file(self.album_path / "track_1.lrc")
        self.delete_file(self.album_path / "disc1" / "track_1.lrc")

        self._run_cli_command("import")

        self.assert_not_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")

    def test_mixed_root_and_disc_content(self) -> None:
        """Verify behavior when an album has tracks at both Root and Disc levels
        (ideally, should never occur).
        E.g. Album/01.mp3 AND Album/CD1/01.mp3.
        """
        config["filetote"]["extensions"] = [".txt", ".file"]

        album_path = self.import_dir / "the_album"

        # Add a track to the Album Root
        self.create_file(album_path / "RootTrack.mp3")
        self.create_file(album_path / "RootArtifact.txt")

        # Run import (expecting Beets to handle the mixed tracks fine)
        self._run_cli_command("import")

        # 1. Verify Disc 1 Artifacts moved
        self.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

        # 2. Verify Root Artifacts moved (associated with RootTrack)
        self.assert_in_lib_dir("Tag Artist/Tag Album/RootArtifact.txt")
