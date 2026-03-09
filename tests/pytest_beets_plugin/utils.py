"""General utility methods for beets plugin tests."""

import logging

from pathlib import Path

from beets import util

log = logging.getLogger("beets")

# Test resources path.
RESOURCES_DIR: Path = Path(__file__).resolve().parent / "resources"
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# More types may be expanded as testing becomes more sophisticated.
SAMPLE_MEDIA_FILES: dict[str, str] = {
    "mp3": "full.mp3",
    "flac": "full.flac",
    "wav": "full.wav",
}


class BeetsTestUtils:
    """Utility methods for beets plugin tests (no test state)."""

    def fmt_path(self, *parts: str) -> str:
        """Join path components into a string using the current OS separator.

        Useful for defining Beets path_formats without using os.path.join.
        """
        return str(Path(*parts))

    def create_file(self, path: Path) -> None:
        """Creates a file in a specific location, ensuring the parent directories
        exist.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def delete_file(self, path: Path) -> None:
        """Delete a file at a specific location, if it exists."""
        if path.exists():
            path.unlink()

    def _log_indenter(self, indent_level: int) -> str:
        return " " * 4 * indent_level

    def list_files(self, startpath: Path) -> None:
        """Provide a formatted list of files, directories, and their contents in
        logs.
        """
        if not startpath.exists():
            log.debug(f"{startpath} does not exist")
            return

        for root, _dirs, files in util.sorted_walk(startpath):
            root_path = Path(util.displayable_path(root))

            try:
                relative_path = root_path.relative_to(startpath)
                level = len(relative_path.parts)
            except ValueError:
                level = 0

            indent = self._log_indenter(level)
            log_string = f"{indent}{root_path.name}/"
            log.debug(log_string)

            subindent = self._log_indenter(level + 1)
            for filename in files:
                sub_log_string = f"{subindent}{util.displayable_path(filename)}"
                log.debug(sub_log_string)

    def get_rsrc_from_extension(self, file_ext: str) -> str:
        """Get the resource file matching extension, defaulting to MP3."""
        file_type = file_ext.lstrip(".").lower()
        return SAMPLE_MEDIA_FILES.get(file_type, SAMPLE_MEDIA_FILES["mp3"])


# Backward-compatible alias
HelperUtils = BeetsTestUtils
