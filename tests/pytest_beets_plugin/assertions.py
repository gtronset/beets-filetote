"""Assertion helpers for beets plugin tests."""

from pathlib import Path


class BeetsAssertions:
    """A mixin with additional test assertions for beets plugins."""

    @staticmethod
    def assert_exists(path: Path) -> None:
        """Assert that a file exists."""
        assert path.exists(), f"file does not exist: {path!s}"

    @staticmethod
    def assert_does_not_exist(path: Path) -> None:
        """Assert that a file does not exist."""
        assert not path.exists(), f"file exists: {path!s}"

    @staticmethod
    def assert_equal_path(path_a: Path, path_b: Path) -> None:
        """Check that two paths point to the same resolved location."""
        path_a_full = path_a.resolve()
        path_b_full = path_b.resolve()

        assert path_a_full == path_b_full, (
            f"paths are not equal: {path_a!s} and {path_b!s}"
        )


AssertionsMixin = BeetsAssertions
