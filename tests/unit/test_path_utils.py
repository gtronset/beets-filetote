"""Tests for the filesystem utility functions in `path_utils`."""

import os

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.pytest_beets_plugin import load_plugin_source

path_utils = load_plugin_source("path_utils")


class TestPathUtils:
    """Test suite for path_utils module."""

    @pytest.mark.parametrize(
        "input_val",
        [b"foo/bar", "foo/bar", Path("foo/bar")],
        ids=["bytes", "str", "Path"],
    )
    def test_to_path(self, input_val: bytes | str | Path) -> None:
        """Test conversion of bytes and strings to Path. Ensures a noop for Path."""
        assert path_utils.to_path(input_val) == Path("foo/bar")

    @pytest.mark.parametrize(
        ("extension", "expected"),
        [
            (".mp3", True),
            (".flac", True),
            (".jpg", False),
            ("mp3", False),  # preceding dot is required
        ],
    )
    def test_is_beets_file_type(self, extension: str, expected: bool) -> None:
        """Test beets file type detection."""
        types = {"mp3": "MPEG", "flac": "FLAC"}
        assert path_utils.is_beets_file_type(extension, types) is expected

    def test_discover_artifacts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test artifact discovery and ignoring of beets-handled files. Mock
        `sorted_walk` to control the filesystem structure.
        """
        walk_result: list[tuple[bytes, list[bytes], list[bytes]]] = [
            (b"/music/album", [], [b"cover.jpg", b"song.mp3"])
        ]

        def mock_sorted_walk(
            *_args: object, **_kwargs: object
        ) -> Iterator[tuple[bytes, list[bytes], list[bytes]]]:
            yield from walk_result

        monkeypatch.setattr(path_utils.util, "sorted_walk", mock_sorted_walk)

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
        assert is_match is True
        assert match_category == "images"

        is_not_match, no_match_category = path_utils.is_pattern_match(
            Path("cover.png"), patterns
        )
        assert is_not_match is False
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

    @pytest.mark.parametrize(
        ("extension", "allowed", "expected"),
        [
            (".jpg", [".*"], True),
            (".nfo", [".*"], True),
            (".log", [".log"], True),
            (".txt", [".log"], False),
        ],
    )
    def test_is_allowed_extension(
        self, extension: str, allowed: list[str], expected: bool
    ) -> None:
        """Test extension whitelist logic. The underlying configuration defaults and
        passes through the wildcard `.*` to allow all extensions, so we test that, too.
        """
        assert path_utils.is_allowed_extension(extension, allowed) is expected

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

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            # Basic cases
            ("CD1", True),
            ("CD 01", True),
            ("Disc 1", True),
            ("Disc01", True),
            ("disk 1", True),
            # Case insensitivity
            ("cd 1", True),
            ("DISC 2", True),
            # Separator variations ([\W_]*)
            ("CD-1", True),
            ("CD_1", True),
            ("CD.1", True),
            ("CD - 01", True),
            # Complex prefixes (regex allows ".*" before marker)
            ("Album Name CD1", True),
            ("Album Name - Disc 2", True),
            # Nested subdirectories
            ("music/Album/CD1", True),
            # No digit at end
            ("CD", False),
            ("Disc", False),
            ("CD Extras", False),
            ("Disc Art", False),
            # Non-Disk/CD text
            ("Bonus", False),
            ("Artwork", False),
            # Word characters after disk/CD but before digits
            ("Disk No. 1", False),
            ("CD Volume 1", False),
        ],
    )
    def test_is_multidisc(self, path: str, expected: bool) -> None:
        """Test multi-disc directory regex."""
        assert path_utils.is_multidisc(Path(path)) is expected

    def test_get_multidisc_ignore_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that multi-disc directories are correctly identified for ignoring."""
        multidisc_parent_path = Path("/music/album")

        dir_entries = [
            SimpleNamespace(name="CD1", is_dir=lambda: True),
            SimpleNamespace(name="CD2", is_dir=lambda: True),
            SimpleNamespace(name="Bonus", is_dir=lambda: True),
            SimpleNamespace(name="CD3.txt", is_dir=lambda: False),
        ]

        monkeypatch.setattr(Path, "iterdir", lambda _self: dir_entries)

        ignore_paths = path_utils.get_multidisc_ignore_paths(multidisc_parent_path)

        assert "CD1" in ignore_paths
        assert "CD2" in ignore_paths
        assert "Bonus" not in ignore_paths
        assert "CD3.txt" not in ignore_paths
