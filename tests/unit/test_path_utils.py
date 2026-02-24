"""Tests for the filesystem utility functions in `path_utils`."""

from __future__ import annotations

import os
import unittest

from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.helper import import_plugin_module_statically

path_utils = import_plugin_module_statically("path_utils")


class TestPathUtils(unittest.TestCase):
    """Test suite for path_utils module."""

    def test_to_path(self) -> None:
        """Test conversion of bytes and strings to Path. Ensures a noop for Path when
        given.
        """
        assert path_utils.to_path(b"foo/bar") == Path("foo/bar")
        assert path_utils.to_path("foo/bar") == Path("foo/bar")
        assert path_utils.to_path(Path("foo/bar")) == Path("foo/bar")

    def test_is_beets_file_type(self) -> None:
        """Test beets file type detection. `beets_file_types` is an evolving dict, but
        basic logic can be tested.
        """
        types = {"mp3": "MPEG", "flac": "FLAC"}

        assert path_utils.is_beets_file_type(".mp3", types)
        assert path_utils.is_beets_file_type(".flac", types)

        assert not path_utils.is_beets_file_type(".jpg", types)
        # Ensure a preceding dot (`.`) is required
        assert not path_utils.is_beets_file_type("mp3", types)

    @patch("beetsplug.path_utils.util.sorted_walk")
    def test_discover_artifacts(self, mock_walk: MagicMock) -> None:
        """Test artifact discovery and ignoring of beets-handled files. Mock
        `sorted_walk` to control the filesystem structure.
        """
        mock_walk.return_value = [(b"/music/album", [], [b"cover.jpg", b"song.mp3"])]

        beets_types = {"mp3": "Audio"}
        ignore_list = ["*.nfo"]  # Not actually used due to the mocked file list

        artifacts = path_utils.discover_artifacts(
            Path("/music/album"), ignore=ignore_list, beets_file_types=beets_types
        )

        filenames = [artifact.name for artifact in artifacts]

        assert "cover.jpg" in filenames
        assert "song.mp3" not in filenames

    def test_is_pattern_match_exact(self) -> None:
        """Test exact file pattern matching."""
        patterns = {"images": ["*.jpg"]}

        is_match, match_category = path_utils.is_pattern_match(
            Path("cover.jpg"), patterns
        )
        assert is_match
        assert match_category == "images"

        is_not_match, no_match_category = path_utils.is_pattern_match(
            Path("cover.png"), patterns
        )
        assert not is_not_match
        assert no_match_category is None

    def test_is_pattern_match_directory_normalization(self) -> None:
        """Test that directory patterns (ending in /) are normalized and matched."""
        patterns = {"scans": ["Scans/"]}

        artifact = Path("Scans/booklet.jpg")

        is_match, match_category = path_utils.is_pattern_match(artifact, patterns)

        assert is_match, "Should match directory pattern 'Scans/'"
        assert match_category == "scans"

    def test_is_pattern_match_mixed_separators(self) -> None:
        r"""Test that Windows-style config works on generic OS via normalization. Note:
        This test relies on os.sep of the runner.

        - If on Linux/Mac, 'Documentation\' is replaced by 'Documentation/'
        - If on Windows, 'Documentation\' stays 'Documentation\'
        """
        patterns = {"docs": ["Documentation\\"]}

        artifact = Path("Documentation/readme.txt")

        is_match, _match_category = path_utils.is_pattern_match(artifact, patterns)
        assert is_match

    def test_get_artifact_subpath(self) -> None:
        """Test extracting subpaths."""
        source_path = Path("/music/album")

        artifact_path = Path("/music/album/subfolder/cover.jpg")
        subpath = path_utils.get_artifact_subpath(source_path, artifact_path)
        assert "subfolder" in subpath

        # Expect ends with path separator
        assert subpath.endswith(os.sep)

        artifact_path2 = Path("/music/album/subfolder1/subfolder2/cover.jpg")
        subpath2 = path_utils.get_artifact_subpath(source_path, artifact_path2)
        assert "subfolder2" in subpath2

        # Ensure different root paths don't produce a subpath
        different_artifact_path = Path("/audiobooks/album/cover.jpg")
        subpath_empty1 = path_utils.get_artifact_subpath(
            source_path, different_artifact_path
        )
        assert not subpath_empty1

        # Ensure that if the artifact is directly in the source path, we get an empty
        # subpath (not a separator or ".")
        non_subpath_artifact_root = Path("/music/album/cover.jpg")
        subpath_empty2 = path_utils.get_artifact_subpath(
            source_path, non_subpath_artifact_root
        )
        assert not subpath_empty2

    def test_is_allowed_extension(self) -> None:
        """Test extension whitelist logic. The underlying configuration defaults and
        passes through the wildcard `.*` to allow all extensions, so we test that, too.
        """
        allowed = [".*"]
        assert path_utils.is_allowed_extension(".jpg", allowed)
        assert path_utils.is_allowed_extension(".nfo", allowed)

        allowed_strict = [".log"]
        assert path_utils.is_allowed_extension(".log", allowed_strict)
        assert not path_utils.is_allowed_extension(".txt", allowed_strict)

    def test_get_prune_root_path(self) -> None:
        """Test logic for deciding where to prune empty dirs."""
        lib_path = Path("/val/music")
        import_path = Path("/home/user/downloads/album")
        source_path = import_path
        artifact = import_path / "art.jpg"

        # No import path -> Lib path
        assert (
            path_utils.get_prune_root_path(source_path, artifact, lib_path, None)
            == lib_path
        )

        # Import == Lib -> Lib Parent
        assert (
            path_utils.get_prune_root_path(source_path, artifact, lib_path, lib_path)
            == lib_path.parent
        )

        # Import path is different -> Import Path
        assert (
            path_utils.get_prune_root_path(source_path, artifact, lib_path, import_path)
            == import_path
        )

    def test_is_multidisc(self) -> None:
        """Test multi-disc directory regex."""
        # Basic cases
        assert path_utils.is_multidisc(Path("CD1"))
        assert path_utils.is_multidisc(Path("CD 01"))
        assert path_utils.is_multidisc(Path("Disc 1"))
        assert path_utils.is_multidisc(Path("Disc01"))
        assert path_utils.is_multidisc(Path("disk 1"))

        # Case insensitivity
        assert path_utils.is_multidisc(Path("cd 1"))
        assert path_utils.is_multidisc(Path("DISC 2"))

        # Separator variations ([\W_]*)
        assert path_utils.is_multidisc(Path("CD-1"))
        assert path_utils.is_multidisc(Path("CD_1"))
        assert path_utils.is_multidisc(Path("CD.1"))
        assert path_utils.is_multidisc(Path("CD - 01"))

        # Complex prefixes (regex allows ".*" before marker)
        assert path_utils.is_multidisc(Path("Album Name CD1"))
        assert path_utils.is_multidisc(Path("Album Name - Disc 2"))

        # Test nested subdirectories
        assert path_utils.is_multidisc(Path("music/Album/CD1"))

        # No digit at end
        assert not path_utils.is_multidisc(Path("CD"))
        assert not path_utils.is_multidisc(Path("Disc"))
        assert not path_utils.is_multidisc(Path("CD Extras"))
        assert not path_utils.is_multidisc(Path("Disc Art"))

        # Non-Disk/CD text
        assert not path_utils.is_multidisc(Path("Bonus"))
        assert not path_utils.is_multidisc(Path("Artwork"))

        # Word characters after disk/CD but before digits
        assert not path_utils.is_multidisc(Path("Disk No. 1"))
        assert not path_utils.is_multidisc(Path("CD Volume 1"))

    @patch("pathlib.Path.iterdir")
    def test_get_multidisc_ignore_paths(self, mock_iterdir: MagicMock) -> None:
        """Test that multi-disc directories are correctly identified for ignoring."""
        multidisc_parent_path = Path("/music/album")

        cd1 = MagicMock(spec=Path)
        cd1.name = "CD1"
        cd1.is_dir.return_value = True

        cd2 = MagicMock(spec=Path)
        cd2.name = "CD2"
        cd2.is_dir.return_value = True

        bonus = MagicMock(spec=Path)
        bonus.name = "Bonus"
        bonus.is_dir.return_value = True

        file_item = MagicMock(spec=Path)
        file_item.name = "CD3.txt"
        file_item.is_dir.return_value = False

        mock_iterdir.return_value = [cd1, cd2, bonus, file_item]

        ignore_paths = path_utils.get_multidisc_ignore_paths(multidisc_parent_path)

        assert "CD1" in ignore_paths
        assert "CD2" in ignore_paths
        assert "Bonus" not in ignore_paths
        assert "CD3.txt" not in ignore_paths
