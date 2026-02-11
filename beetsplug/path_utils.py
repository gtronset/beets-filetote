"""Utility functions for filesystem operations and path manipulation."""

from __future__ import annotations

import filecmp
import fnmatch
import os
import re

from pathlib import Path
from typing import TYPE_CHECKING

from beets import util
from beets.importer.tasks import MULTIDISC_MARKERS, MULTIDISC_PAT_FMT

if TYPE_CHECKING:
    from collections.abc import Sequence

    from beets.util import PathLike

# Define this buffer once at module level for efficiency
PATH_SEP: str = os.sep
PATH_SEP_BYTES: bytes = PATH_SEP.encode()


def to_path(beets_path: PathLike) -> Path:
    """Converts a beets-style str/bytes path into a pathlib.Path object."""
    return Path(util.displayable_path(beets_path))


def is_beets_file_type(file_ext: str, beets_file_types: dict[str, str]) -> bool:
    """Checks if the provided file extension is a music file/track
    (i.e., already handles by Beets). `file_ext` should include the dot (e.g.,
    '.mp3').
    """
    return len(file_ext) > 1 and util.displayable_path(file_ext)[1:] in beets_file_types


def discover_artifacts(
    source_path: Path, ignore: Sequence[str], beets_file_types: dict[str, str]
) -> list[Path]:
    """Walks a directory and returns a list of all non-beets-handled files."""
    artifacts: list[Path] = []

    for root, _dirs, files in util.sorted_walk(source_path, ignore=ignore):
        for filename in files:
            full_path_bytes = root + PATH_SEP_BYTES + filename

            file_path: Path = to_path(full_path_bytes)

            # Skip any files extensions handled by beets
            if is_beets_file_type(file_path.suffix, beets_file_types=beets_file_types):
                continue

            artifacts.append(file_path)

    return artifacts


def is_pattern_match(
    artifact_relpath: Path,
    patterns_dict: dict[str, list[str]],
    match_category: str | None = None,
) -> tuple[bool, str | None]:
    """Check if the file is in the defined patterns. Pattern path separators are
    normalized to the OS separator. If the pattern ends with a separator, it is
    treated as a directory pattern and matches any file within that directory or its
    subdirectories. If `match_category` is provided, only patterns within that
    category are checked.
    """
    pattern_definitions: list[tuple[str, list[str]]] = list(patterns_dict.items())

    if match_category:
        pattern_definitions = [(match_category, patterns_dict[match_category])]

    for category, patterns in pattern_definitions:
        for pattern in patterns:
            is_match: bool = False

            normalized_pattern: str = pattern.replace("/", PATH_SEP).replace(
                "\\", PATH_SEP
            )

            if normalized_pattern.endswith(PATH_SEP):
                for path in util.ancestry(util.displayable_path(artifact_relpath)):
                    if not fnmatch.fnmatch(
                        util.displayable_path(path),
                        normalized_pattern.strip(PATH_SEP),
                    ):
                        continue
                    is_match = True
            else:
                is_match = fnmatch.fnmatch(
                    util.displayable_path(artifact_relpath),
                    normalized_pattern.lstrip(PATH_SEP),
                )

            if is_match:
                return (is_match, category)

    return (False, None)


def artifact_exists_in_dest(
    artifact_source: Path,
    artifact_dest: Path,
) -> bool:
    """Checks if the artifact/file already exists in the destination."""
    return artifact_dest.exists() and filecmp.cmp(artifact_source, artifact_dest)


def get_artifact_subpath(
    source_path: Path,
    artifact_path: Path,
) -> str:
    """Checks if the artifact/file has a subpath in the source location and returns
    its subpath. This also ensures a trailing separator is present if there's a
    subpath. This is needed for renaming and templates as conditionally using the
    `$subpath` is not supported by plugins such as `inline`.
    """
    if not artifact_path.is_relative_to(source_path):
        return ""

    artifact_parent = artifact_path.parent

    # Check if artifact is directly in the source path
    if artifact_parent == source_path:
        return ""

    relative_path = artifact_parent.relative_to(source_path)

    return util.displayable_path(relative_path) + PATH_SEP


def is_path_within_ancestry(child_path: Path | None, parent_path: Path) -> bool:
    """Checks if a path is a subdirectory of another by checking its ancestry."""
    return child_path is not None and str(parent_path) in util.ancestry(str(child_path))


def is_multi_disc(path_name: Path) -> bool:
    """Checks if a directory name matches the multi-disc pattern by replicating the
    beets importer's pattern matching for disc folders.
    """
    path_name_bytes = util.bytestring_path(path_name.name)

    for marker in MULTIDISC_MARKERS:
        p = MULTIDISC_PAT_FMT.replace(b"%s", marker)
        pat = re.compile(p, re.I)
        if pat.match(path_name_bytes):
            return True

    return False


def is_allowed_extension(extension: str, allowed_extensions: Sequence[str]) -> bool:
    """Checks if an extension is in the allowed list (supports global wildcard '.*')."""
    return (
        ".*" in allowed_extensions
        or util.displayable_path(extension) in allowed_extensions
    )


def is_import_path_same_as_library_path(
    library_path: Path, import_path: Path | None
) -> bool:
    """Checks if the import path matches the library directory."""
    return import_path is not None and import_path == library_path


def is_reimport(library_path: Path, import_path: Path | None) -> bool:
    """Checks if the import is considered a "reimport".

    Copy and link modes treat reimports specially, where in-library files
    are moved.
    """
    return is_import_path_same_as_library_path(
        library_path, import_path
    ) or is_path_within_ancestry(child_path=import_path, parent_path=library_path)


def get_prune_root_path(
    source_path: Path,
    artifact_path: Path,
    library_path: Path,
    import_path: Path | None,
) -> Path | None:
    """Deduces the root path for cleaning up dangling files on MOVE.

    This method determines the root path that aids in cleaning up files
    when moving. If the import path matches the library directory or is
    within it, the root path is selected. Otherwise, returns None.
    """
    root_path: Path | None = None

    if import_path is None:
        # If there's not a import path (query, other CLI, etc.), use the Library's
        # dir instead. This is consistent with beet's default pruning for MOVE.
        root_path = library_path
    elif is_import_path_same_as_library_path(library_path, import_path):
        # If the import path is the same as the Library's, allow for
        # pruning all the way to the library path.
        root_path = library_path.parent
    elif is_path_within_ancestry(child_path=import_path, parent_path=library_path):
        # If the import path is within the Library's, allow for pruning all the way
        # to the import path.
        root_path = import_path
    elif is_path_within_ancestry(
        child_path=artifact_path, parent_path=source_path
    ) or is_multi_disc(source_path):
        # If the artifact is within the source path or is multidisc, prune up to the
        # import path.
        root_path = import_path

    return root_path
