"""Assertion helpers for beets plugin tests.

All assertion logic is consolidated here. Both ``BeetsPluginFixture`` and
the legacy ``Assertions`` class delegate to these functions.
"""

from __future__ import annotations

from pathlib import Path


def assert_exists(path: Path) -> None:
    """Assert that a file exists."""
    assert path.exists(), f"file does not exist: {path!s}"


def assert_does_not_exist(path: Path) -> None:
    """Assert that a file does not exist."""
    assert not path.exists(), f"file exists: {path!s}"


def resolve_relative_path(root: Path, relative_path: str | Path) -> Path:
    """Resolve a relative path against a root, raising on absolute paths."""
    path_obj = Path(relative_path)
    if path_obj.is_absolute():
        msg = f"Path must be relative, got absolute: {path_obj}"
        raise ValueError(msg)
    return root / path_obj


class BeetsAssertions:
    """Mixin providing assertion methods bound to ``lib_dir`` and ``import_dir``.

    Subclasses or composing classes must set ``lib_dir`` and ``import_dir``
    attributes.
    """

    lib_dir: Path
    import_dir: Path

    def assert_exists(self, path: Path) -> None:
        """Assert that a file exists."""
        assert_exists(path)

    def assert_does_not_exist(self, path: Path) -> None:
        """Assert that a file does not exist."""
        assert_does_not_exist(path)

    def assert_equal_path(self, path_a: Path, path_b: Path) -> None:
        """Check that two paths point to the same resolved location."""
        assert path_a.resolve() == path_b.resolve(), (
            f"paths are not equal: {path_a!s} and {path_b!s}"
        )

    def assert_in_lib_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path exists inside the library directory."""
        assert_exists(resolve_relative_path(self.lib_dir, relative_path))

    def assert_not_in_lib_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path does not exist inside the library
        directory.
        """
        assert_does_not_exist(resolve_relative_path(self.lib_dir, relative_path))

    def assert_import_dir_exists(self, check_dir: Path | None = None) -> None:
        """Asserts that the import directory exists."""
        directory = check_dir or self.import_dir
        if directory:
            assert_exists(directory)

    def assert_in_import_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path exists inside the import directory."""
        if self.import_dir:
            assert_exists(resolve_relative_path(self.import_dir, relative_path))

    def assert_not_in_import_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path does not exist inside the import directory."""
        if self.import_dir:
            assert_does_not_exist(resolve_relative_path(self.import_dir, relative_path))

    def assert_islink(self, relative_path: str | Path) -> None:
        """Assert that a path is a symbolic link."""
        if self.lib_dir:
            path = resolve_relative_path(self.lib_dir, relative_path)
            assert path.is_symlink(), f"Expected {path} to be a symbolic link"

    def assert_number_of_files_in_dir(self, count: int, directory: Path) -> None:
        """Assert that there are ``count`` files in the provided path."""
        assert directory.exists(), f"Directory does not exist: {directory}"
        assert directory.is_dir(), f"Path is not a directory: {directory}"
        actual_count = len(list(directory.iterdir()))
        assert actual_count == count, (
            f"Expected {count} files in {directory}, found {actual_count}"
        )


# Backward-compatible alias
AssertionsMixin = BeetsAssertions
