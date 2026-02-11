"""Tests for the filesystem utility functions in `path_utils`."""

from __future__ import annotations

import os
import unittest

from pathlib import Path
from unittest.mock import MagicMock, patch

# from beetsplug import path_utils
from tests.helper import import_plugin_module_statically

path_utils = import_plugin_module_statically("path_utils")


class TestPathUtils(unittest.TestCase):
    """Test suite for path_utils module."""

    def test_to_path(self) -> None:
        """Test conversion of bytes/strings to Path. Ensures a noop for Path when
        given.
        """
        assert path_utils.to_path(b"foo/bar") == Path("foo/bar")
        assert path_utils.to_path("foo/bar") == Path("foo/bar")
        assert path_utils.to_path(Path("foo/bar")) == Path("foo/bar")

    def test_is_beets_file_type(self) -> None:
        """Test beets file type detection. `beets_file_types` is an evolving dict, but
        we can test basic logic.
        """
        types = {"mp3": "MPEG", "flac": "FLAC"}

        assert path_utils.is_beets_file_type(".mp3", types)
        assert path_utils.is_beets_file_type(".flac", types)

        assert not path_utils.is_beets_file_type(".jpg", types)
        # Ensure a preceding dot (`.`) is required
        assert not path_utils.is_beets_file_type("mp3", types)

    @patch("beetsplug.path_utils.util.sorted_walk")
    def test_discover_artifacts(self, mock_walk: MagicMock) -> None:
        """Test artifact discovery and ignoring of beets-handled files. We mock
        `sorted_walk` to control the filesystem structure.
        """
        mock_walk.return_value = [(b"/music/album", [], [b"cover.jpg", b"song.mp3"])]

        beets_types = {"mp3": "Audio"}
        ignore_list = ["*.nfo"]  # Irreleant due to the mocked file list

        artifacts = path_utils.discover_artifacts(
            Path("/music/album"), ignore=ignore_list, beets_file_types=beets_types
        )

        # Expected:
        # - song.mp3 is skipped (beets type)
        # - artifact.nfo is NOT skipped
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
        r"""Test that Windows-style config works on generic OS via normalization.

        If on Linux/Mac, 'Documentation\' is replaced by 'Documentation/'
        If on Windows, 'Documentation\' stays 'Documentation\'
        """
        patterns = {"docs": ["Documentation\\"]}

        artifact = Path("Documentation/readme.txt")

        # Note: This test relies on os.sep of the runner
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

        # Ensure different paths don't produce a subpath
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
        allowed = [".jpg", ".png", ".*"]
        assert path_utils.is_allowed_extension(".jpg", allowed)
        assert path_utils.is_allowed_extension(".nfo", allowed)  # .* matches all

        allowed_strict = [".log"]
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

    def test_is_multi_disc(self) -> None:
        """Test multi-disc directory regex."""
        assert path_utils.is_multi_disc(Path("CD1"))
        assert path_utils.is_multi_disc(Path("disc 02"))
        assert not path_utils.is_multi_disc(Path("Bonus"))
