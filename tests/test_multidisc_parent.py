"""Tests for handling artifacts in parent directories of multi-disc albums."""

import pytest

from tests.pytest_beets_plugin import BeetsEnvFactory


class TestMultidiscParent:
    """Tests that Filetote correctly handles artifacts located in the parent directory
    of a multi-disc album (e.g., `Album/summary.txt` alongside `Album/Disc1/`).
    """

    @pytest.fixture(autouse=True)
    def _setup(self, beets_nested_env: BeetsEnvFactory) -> None:
        """Provides shared setup for tests."""
        self.env = beets_nested_env(
            parent_artifacts=["summary.txt", "artifact.nfo", "artwork/poster.jpg"]
        )

    def test_collects_parent_artifacts(self) -> None:
        """Ensures artifacts in the parent album directory are collected and moved to
        the destination library, alongside the disc contents.
        """
        env = self.env

        env.config["filetote"]["extensions"] = [".file", ".txt", ".nfo", ".jpg"]

        env.run_cli_command("import")

        # Verify standard disc-level artifacts moved (baseline check)
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact2.file")

        # Verify Parent artifacts were moved
        env.assert_in_lib_dir("Tag Artist/Tag Album/summary.txt")
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.nfo")

        # Verify Parent subdirectory artifacts were moved
        env.assert_in_lib_dir("Tag Artist/Tag Album/poster.jpg")

    def test_collects_parent_artifacts_into_disc_paths(self) -> None:
        """Ensures that if the user has a nested library path (`Album/Disc 01/`), the
        parent artifacts are effectively copied/moved relative to the items.

        Ensure that artifacts in the Parent are only processed once.
        """
        env = self.env

        env.config["filetote"]["extensions"] = [".file", ".txt"]

        # Use disc folders: Artist/Album/01/Title.mp3
        env.lib.path_formats = [
            ("default", env.fmt_path("$artist", "$album", "$disc", "$title")),
        ]

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/01/artifact.file")

        # `summary.txt` in the Parent should only be processed once, as part of Disc 01.
        env.assert_in_lib_dir("Tag Artist/Tag Album/01/summary.txt")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/02/summary.txt")

    def test_ignores_sibling_disc_folders(self) -> None:
        """Verify that when processing artifacts for `Disc 1`, artifacts from `Disc 2`
        (sibling folder) are not grabbed while scanning the parent.
        """
        env = self.env
        env.config["filetote"]["extensions"] = ".file"

        # Use disc folders to verify artifacts stay with their own disc.
        env.lib.path_formats = [
            ("default", env.fmt_path("$artist", "$album", "$disc", "$title")),
        ]

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/01/artifact.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/02/artifact.file")

        env.assert_in_lib_dir("Tag Artist/Tag Album/02/artifact3.file")
        env.assert_not_in_lib_dir("Tag Artist/Tag Album/01/artifact3.file")

    def test_preserves_parent_structure_with_pattern(self) -> None:
        """Verify that original structure for Parent artifacts can be recreated."""
        env = self.env
        env.config["filetote"]["extensions"] = ".jpg"
        env.config["filetote"]["paths"] = {
            "pattern:artwork": "$albumpath/artwork/$old_filename"
        }
        env.config["filetote"]["patterns"] = {"artwork": ["artwork/*.jpg"]}

        env.run_cli_command("import")

        env.assert_in_lib_dir("Tag Artist/Tag Album/artwork/poster.jpg")

    def test_parent_artifacts_do_not_pair_with_subdirectory_tracks(self) -> None:
        """Verify that an artifact in the Parent folder ("Aunt") does NOT pair with a
        track in a Subdirectory ("Niece"), even if names match.

        Example: `Album/01.lrc` should NOT pair with `Album/CD1/01.mp3`.
        """
        env = self.env
        env.config["filetote"]["extensions"] = ".lrc"
        env.config["filetote"]["pairing"] = {
            "enabled": True,
            "pairing_only": True,
        }

        album_path = env.import_dir / "the_album"

        env.create_file(album_path / "track_1.lrc")
        env.delete_file(album_path / "disc1" / "track_1.lrc")

        env.run_cli_command("import")

        env.assert_not_in_lib_dir("Tag Artist/Tag Album/Tag Title 1.lrc")

    def test_mixed_root_and_disc_content(self) -> None:
        """Verify behavior when an album has tracks at both Root and Disc levels
        (ideally, should never occur).

        E.g. `Album/01.mp3` AND `Album/CD1/01.mp3`.
        """
        env = self.env
        env.config["filetote"]["extensions"] = [".txt", ".file"]

        album_path = env.import_dir / "the_album"

        # Add a track to the Album Root
        env.create_file(album_path / "RootTrack.mp3")
        env.create_file(album_path / "RootArtifact.txt")

        # Run import (expecting Beets to handle the mixed tracks fine)
        env.run_cli_command("import")

        # 1. Verify Disc 1 Artifacts moved
        env.assert_in_lib_dir("Tag Artist/Tag Album/artifact.file")

        # 2. Verify Root Artifacts moved (associated with RootTrack)
        env.assert_in_lib_dir("Tag Artist/Tag Album/RootArtifact.txt")
