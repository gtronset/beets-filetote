"""BeetsPluginFixture: the main test helper object for beets plugin tests."""

# from __future__ import annotations

import logging
import shutil

from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from beets import config, library, plugins, util
from beets.importer import ImportSession
from mediafile import MediaFile

from ._item_model import MediaMeta
from .helper import RSRC, BeetsTestUtils, MediaSetup
from .plugin_lifecycle import _load_plugins, _unload_plugins

# TODO(gtronset): Remove this once beets 2.4 and 2.5 are no longer supported.
# https://github.com/gtronset/beets-filetote/pull/253
try:
    from beets.ui.commands.modify import modify_items
    from beets.ui.commands.move import move_items
    from beets.ui.commands.update import update_items
except ImportError:
    from beets.ui.commands import (
        modify_items,
        move_items,
        update_items,
    )


log = logging.getLogger("beets")


class BeetsPluginFixture(BeetsTestUtils):
    """A non-TestCase helper providing the same API as FiletoteTestCase.

    Designed to be generic for any beets plugin's test suite.
    """

    def __init__(
        self,
        tmp_path: Path,
        lib: library.Library,
        lib_dir: Path,
        import_dir: Path,
        other_plugins: list[str] | None = None,
    ) -> None:
        """Handles all setup for testing, including library (database)."""
        self.temp_dir = tmp_path
        self.lib = lib
        self.lib_dir = lib_dir
        self.import_dir = import_dir
        self.plugins = other_plugins or []

        self.rsrc_mp3: str = "full.mp3"
        self._media_count: int = 0
        self._pairs_count: int = 0
        self.import_media: list[MediaFile] | None = None
        self.importer: ImportSession | None = None
        self.paths: Path | None = None

    # --- Assertions ---------------------------------------------------------

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
        assert path_a.resolve() == path_b.resolve(), (
            f"paths are not equal: {path_a!s} and {path_b!s}"
        )

    def _resolve_relative_path(self, root: Path, relative_path: str | Path) -> Path:
        path_obj = Path(relative_path)
        if path_obj.is_absolute():
            msg = f"Path must be relative, got absolute: {path_obj}"
            raise ValueError(msg)
        return root / path_obj

    def assert_in_lib_dir(self, relative_path: str | Path) -> None:
        """Assert that a file exists relative to the library directory."""
        self.assert_exists(self._resolve_relative_path(self.lib_dir, relative_path))

    def assert_not_in_lib_dir(self, relative_path: str | Path) -> None:
        """Assert that a file does not exist relative to the library dir."""
        self.assert_does_not_exist(
            self._resolve_relative_path(self.lib_dir, relative_path)
        )

    def assert_import_dir_exists(self, check_dir: Path | None = None) -> None:
        """Assert that the import directory (or given directory) exists."""
        directory = check_dir or self.import_dir
        if directory:
            self.assert_exists(directory)

    def assert_in_import_dir(self, relative_path: str | Path) -> None:
        """Assert that a file exists relative to the import directory."""
        if self.import_dir:
            self.assert_exists(
                self._resolve_relative_path(self.import_dir, relative_path)
            )

    def assert_not_in_import_dir(self, relative_path: str | Path) -> None:
        """Assert that a file does not exist relative to the import dir."""
        if self.import_dir:
            self.assert_does_not_exist(
                self._resolve_relative_path(self.import_dir, relative_path)
            )

    def assert_islink(self, relative_path: str | Path) -> None:
        """Assert that a path in the library directory is a symbolic link."""
        path = self._resolve_relative_path(self.lib_dir, relative_path)
        assert path.is_symlink(), f"Expected {path} to be a symbolic link"

    def assert_number_of_files_in_dir(self, count: int, directory: Path) -> None:
        """Assert that a directory contains exactly ``count`` entries."""
        assert directory.exists(), f"Directory does not exist: {directory}"
        assert directory.is_dir(), f"Path is not a directory: {directory}"
        actual_count = len(list(directory.iterdir()))
        assert actual_count == count, (
            f"Expected {count} files in {directory}, found {actual_count}"
        )

    # --- Media creation -----------------------------------------------------

    def create_medium(
        self, path: Path, media_meta: MediaMeta | None = None
    ) -> MediaFile:
        """Create a media file at ``path`` with the given metadata."""
        if media_meta is None:
            media_meta = MediaMeta()

        path.parent.mkdir(parents=True, exist_ok=True)

        resource_name = self.get_rsrc_from_extension(path.suffix)
        resource_path = RSRC / resource_name
        shutil.copy(resource_path, path)
        medium = MediaFile(str(path))

        for item, value in asdict(media_meta).items():
            setattr(medium, item, value)
        medium.save()
        return medium

    def update_medium(self, path: Path, meta_updates: dict[str, str]) -> None:
        """Update metadata on an existing media file."""
        medium = MediaFile(str(path))
        for item, value in meta_updates.items():
            setattr(medium, item, value)
        medium.save()

    # --- Import directory creation ------------------------------------------

    def _set_import_dir(self) -> None:
        if self.import_dir.is_dir():
            shutil.rmtree(self.import_dir)

    def _generate_paired_media_list(  # noqa: PLR0913
        self,
        album_path: Path,
        count: int = 3,
        generate_pair: bool = True,
        pair_subfolders: bool = False,
        filename_prefix: str = "track_",
        file_type: str = "mp3",
        title_prefix: str = "Tag Title ",
        disc: int = 1,
        disctotal: int = 1,
    ) -> list[MediaFile]:
        media_list: list[MediaFile] = []

        while count > 0:
            trackname = f"{filename_prefix}{count}"
            media_path = album_path / f"{trackname}.{file_type}"

            media_list.append(
                self.create_medium(
                    path=media_path,
                    media_meta=MediaMeta(
                        title=f"{title_prefix}{count}",
                        track=count,
                        disc=disc,
                        disctotal=disctotal,
                    ),
                )
            )
            count -= 1

            if generate_pair:
                pair_path: Path = album_path

                if pair_subfolders:
                    pair_path = album_path / "lyrics" / "lyric-subfolder"

                pair_path.mkdir(parents=True, exist_ok=True)
                self.create_file(pair_path / f"{trackname}.lrc")

        return media_list

    def create_flat_import_dir(
        self,
        media_files: list[MediaSetup] | None = None,
        pair_subfolders: bool = False,
    ) -> None:
        """Create a flat (single-disc) import directory structure."""
        if media_files is None:
            media_files = [MediaSetup(pair_subfolders=pair_subfolders)]

        self._set_import_dir()

        album_path: Path = self.import_dir / "the_album"
        album_path.mkdir(parents=True, exist_ok=True)

        artifacts = [
            "artifact.file",
            "artifact2.file",
            "artifact.nfo",
            "artifact.lrc",
        ]

        for artifact in artifacts:
            self.create_file(album_path / artifact)

        media_file_count: int = 0
        media_list: list[MediaFile] = []

        for media_file in media_files:
            media_file_count += media_file.count

            media_list.extend(
                self._generate_paired_media_list(
                    album_path=album_path,
                    file_type=media_file.file_type,
                    count=media_file.count,
                    generate_pair=media_file.generate_pair,
                    pair_subfolders=media_file.pair_subfolders,
                )
            )

        self._media_count = self._pairs_count = media_file_count
        self.import_media = media_list

        log.debug("--- import directory created")
        self.list_files(self.import_dir)

    def create_nested_import_dir(
        self,
        disc1_media_files: list[MediaSetup] | None = None,
        disc2_media_files: list[MediaSetup] | None = None,
    ) -> None:
        """Create a nested (multi-disc) import directory structure."""
        if disc1_media_files is None:
            disc1_media_files = [MediaSetup()]

        if disc2_media_files is None:
            disc2_media_files = [MediaSetup()]

        self._set_import_dir()

        album_path: Path = self.import_dir / "the_album"
        disc1_path: Path = album_path / "disc1"
        disc2_path: Path = album_path / "disc2"

        disc1_path.mkdir(parents=True)
        disc2_path.mkdir(parents=True)

        disc1_artifacts = [
            "artifact.file",
            "artifact2.file",
            "artifact_disc1.nfo",
        ]

        for artifact in disc1_artifacts:
            self.create_file(disc1_path / artifact)

        disc2_artifacts = [
            "artifact3.file",
            "artifact4.file",
            "artifact_disc2.nfo",
        ]

        for artifact in disc2_artifacts:
            self.create_file(disc2_path / artifact)

        media_file_count: int = 0
        media_list: list[MediaFile] = []

        for media_file in disc1_media_files:
            media_file_count += media_file.count

            media_list.extend(
                self._generate_paired_media_list(
                    album_path=disc1_path,
                    file_type=media_file.file_type,
                    count=media_file.count,
                    generate_pair=media_file.generate_pair,
                    disctotal=2,
                )
            )

        for media_file in disc2_media_files:
            media_file_count += media_file.count

            media_list.extend(
                self._generate_paired_media_list(
                    album_path=disc2_path,
                    filename_prefix="supertrack_",
                    file_type=media_file.file_type,
                    count=media_file.count,
                    generate_pair=media_file.generate_pair,
                    title_prefix="Super Tag Title ",
                    disc=2,
                    disctotal=2,
                )
            )

        self._pairs_count = media_file_count
        self._media_count = media_file_count
        self.import_media = media_list

        log.debug("--- import directory created")
        self.list_files(self.import_dir)

    # --- Import session setup -----------------------------------------------

    def setup_import_session(  # noqa: PLR0913
        self,
        import_dir: Path | None = None,
        delete: bool = False,
        threaded: bool = False,
        copy: bool = True,
        singletons: bool = False,
        move: bool = False,
        autotag: bool = True,
        query: str | None = None,
    ) -> None:
        """Configure an ``ImportSession`` for the test."""
        config["import"]["copy"] = copy
        config["import"]["delete"] = delete
        config["import"]["timid"] = True
        config["threaded"] = threaded
        config["import"]["singletons"] = singletons
        config["import"]["move"] = move
        config["import"]["autotag"] = autotag
        config["import"]["resume"] = False

        if not import_dir and not query:
            import_dir = self.import_dir

        self.paths = import_dir

        import_path: list[bytes] = (
            [util.bytestring_path(import_dir)] if import_dir else []
        )

        self.importer = ImportSession(
            self.lib,
            loghandler=None,
            paths=import_path,
            query=query,
        )

    # --- CLI command runners ------------------------------------------------

    def run_cli_command(
        self,
        command: Literal["import", "modify", "move", "update"],
        **kwargs: Any,
    ) -> None:
        """Run a beets CLI command with plugins loaded."""
        log_string = f"Running CLI: {command}"
        log.debug(log_string)

        _load_plugins(self.plugins)

        command_func = getattr(self, f"_run_cli_{command}")
        command_func(**kwargs)

        plugins.send("cli_exit", lib=self.lib)
        _unload_plugins()

        log.debug("--- library structure")
        self.list_files(self.lib_dir)

        if self.paths:
            log.debug("--- source structure after import")
            self.list_files(self.paths)

    def _run_cli_import(
        self, operation_option: Literal["copy", "move"] | None = None
    ) -> None:
        if not self.importer:
            return

        if operation_option == "copy":
            config["import"]["copy"] = True
            config["import"]["move"] = False
        elif operation_option == "move":
            config["import"]["copy"] = False
            config["import"]["move"] = True

        self.importer.run()

    def _run_cli_move(  # noqa: PLR0913
        self,
        query: str,
        dest_dir: bytes | None = None,
        album: str | None = None,
        copy: bool = False,
        pretend: bool = False,
        export: bool = False,
    ) -> None:
        move_items(
            self.lib,
            dest_dir,
            query=query,
            copy=copy,
            album=album,
            pretend=pretend,
            confirm=False,
            export=export,
        )

    def _run_cli_modify(  # noqa: PLR0913
        self,
        query: str,
        mods: dict[str, str] | None = None,
        dels: dict[str, str] | None = None,
        write: bool = True,
        move: bool = True,
        album: str | None = None,
    ) -> None:
        mods = mods or {}
        dels = dels or {}

        modify_items(
            lib=self.lib,
            mods=mods,
            dels=dels,
            query=query,
            write=write,
            move=move,
            album=album,
            confirm=False,
            inherit=True,
        )

    def _run_cli_update(
        self,
        query: str,
        album: str | None = None,
        move: bool = True,
        pretend: bool = False,
        fields: list[str] | None = None,
    ) -> None:
        update_items(
            lib=self.lib,
            query=query,
            album=album,
            move=move,
            pretend=pretend,
            fields=fields,
        )
