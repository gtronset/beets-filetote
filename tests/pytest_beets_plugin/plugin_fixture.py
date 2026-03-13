"""BeetsPluginFixture: the main test helper object for beets plugin tests."""

import contextlib
import logging
import shutil

from collections.abc import Generator
from pathlib import Path
from typing import Any, Literal

from beets import config, library, plugins, util
from beets.importer import ImportSession
from mediafile import MediaFile

from ._item_model import MediaMeta
from .assertions import BeetsAssertions
from .logging import LogLevels, capture_beets_log
from .media import MediaCreator, MediaSetup
from .plugin_lifecycle import _activate_plugins, _deactivate_plugins

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


class BeetsPluginFixture(BeetsAssertions, MediaCreator):
    """A non-TestCase helper providing the same API as FiletoteTestCase.

    Composes:
    - `BeetsAssertions` for all assertion methods
    - `MediaCreator` (extends `BeetsTestUtils`) for media/file operations

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
        self.media_count: int = 0
        self.pairs_count: int = 0
        self.import_media: list[MediaFile] | None = None
        self.importer: ImportSession | None = None
        self.paths: Path | None = None

    @property
    def log(self) -> logging.Logger:
        """Logger for use in tests.

        Avoids needing `import logging` in test files:

            env.log.debug("current config: %s", env.config.dump())
        """
        return log

    @property
    def config(self) -> Any:
        """Access the beets global configuration.

        Eliminates the need for `from beets import config` in test files:

            env.config["filetote"]["extensions"] = ".file"
            env.config["import"]["move"] = True
        """
        return config

    @contextlib.contextmanager
    def capture_log(
        self,
        logger_name: str = "beets",
        level: LogLevels = logging.DEBUG,
    ) -> Generator[list[str], None, None]:
        """Capture log messages from a named logger.

        Sets `config["verbose"]` appropriately for the requested level, then delegates
        to `.logging.capture_beets_log`:

            with env.capture_log("beets.filetote") as logs:
                env.run_cli_command("import")
            assert "filetote: Ignored files:" in logs
        """
        original_verbose = config["verbose"].get()

        if level <= logging.DEBUG:
            config["verbose"] = 2
        elif level <= logging.INFO:
            config["verbose"] = 1
        else:
            config["verbose"] = 0

        try:
            with capture_beets_log(logger_name, level) as messages:
                yield messages
        finally:
            config["verbose"] = original_verbose

    # --- Import directory creation ------------------------------------------

    def _reset_import_dir(self) -> None:
        """Reset the import directory by deleting it if it exists. This is needed for
        tests that do reimports and/or multiple actions in its runs.
        """
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
    ) -> tuple[list[MediaFile], int]:
        media_list: list[MediaFile] = []
        pairs_generated: int = 0

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
                pairs_generated += 1

        return media_list, pairs_generated

    def create_simple_import_dir(
        self,
        artifacts: list[str] | None = None,
        media_count: int = 1,
        file_type: str = "mp3",
    ) -> Path:
        """Create a minimal import directory with artifacts and media."""
        self._reset_import_dir()

        album_path: Path = self.import_dir / "the_album"
        album_path.mkdir(parents=True, exist_ok=True)

        for artifact in artifacts or []:
            self.create_file(album_path / artifact)

        media_list: list[MediaFile] = [
            self.create_medium(album_path / f"track_{i}.{file_type}")
            for i in range(1, media_count + 1)
        ]

        self.media_count = media_count
        self.pairs_count = 0
        self.import_media = media_list

        log.debug("--- import directory created")
        self.list_files(self.import_dir)

        return album_path

    def create_flat_import_dir(
        self,
        media_files: list[MediaSetup] | None = None,
        pair_subfolders: bool = False,
    ) -> Path:
        """Create a flat (single-disc) import directory structure."""
        if media_files is None:
            media_files = [MediaSetup(pair_subfolders=pair_subfolders)]

        self._reset_import_dir()

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
        pairs_count: int = 0
        media_list: list[MediaFile] = []

        for media_file in media_files:
            media_file_count += media_file.count

            generated_media, generated_pairs = self._generate_paired_media_list(
                album_path=album_path,
                file_type=media_file.file_type,
                count=media_file.count,
                generate_pair=media_file.generate_pair,
                pair_subfolders=media_file.pair_subfolders,
            )

            media_list.extend(generated_media)
            pairs_count += generated_pairs

        self.media_count = media_file_count
        self.pairs_count = pairs_count
        self.import_media = media_list

        log.debug("--- import directory created")
        self.list_files(self.import_dir)

        return album_path

    def create_nested_import_dir(
        self,
        disc1_media_files: list[MediaSetup] | None = None,
        disc2_media_files: list[MediaSetup] | None = None,
        parent_artifacts: list[str] | None = None,
    ) -> Path:
        """Create a nested (multi-disc) import directory structure."""
        if disc1_media_files is None:
            disc1_media_files = [MediaSetup()]

        if disc2_media_files is None:
            disc2_media_files = [MediaSetup()]

        self._reset_import_dir()

        album_path: Path = self.import_dir / "the_album"
        disc1_path: Path = album_path / "disc1"
        disc2_path: Path = album_path / "disc2"

        disc1_path.mkdir(parents=True)
        disc2_path.mkdir(parents=True)

        for artifact in parent_artifacts or []:
            artifact_path = album_path / artifact
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            self.create_file(artifact_path)

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
        pairs_count: int = 0
        media_list: list[MediaFile] = []

        for media_file in disc1_media_files:
            media_file_count += media_file.count

            generated_media, generated_pairs = self._generate_paired_media_list(
                album_path=disc1_path,
                file_type=media_file.file_type,
                count=media_file.count,
                generate_pair=media_file.generate_pair,
                disctotal=2,
            )

            media_list.extend(generated_media)
            pairs_count += generated_pairs

        for media_file in disc2_media_files:
            media_file_count += media_file.count

            generated_media, generated_pairs = self._generate_paired_media_list(
                album_path=disc2_path,
                filename_prefix="supertrack_",
                file_type=media_file.file_type,
                count=media_file.count,
                generate_pair=media_file.generate_pair,
                title_prefix="Super Tag Title ",
                disc=2,
                disctotal=2,
            )

            media_list.extend(generated_media)
            pairs_count += generated_pairs

        self.media_count = media_file_count
        self.pairs_count = pairs_count
        self.import_media = media_list

        log.debug("--- import directory created")
        self.list_files(self.import_dir)

        return album_path

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
        """Configure an `ImportSession` for the test."""
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
        """Load plugins, run a CLI command, unload plugins, and log results.

        This is a convenience method that can be called to set-up, exercise,
        and tear-down the system under test after setting any config options
        and before assertions are made regarding changes to the filesystem.
        """
        log_string = f"Running CLI: {command}"
        log.debug(log_string)

        _activate_plugins(self.plugins)

        command_func = getattr(self, f"_run_cli_{command}")
        command_func(**kwargs)

        plugins.send("cli_exit", lib=self.lib)
        _deactivate_plugins()

        log.debug("--- library structure")
        self.list_files(self.lib_dir)

        if self.paths:
            log.debug("--- source structure after import")
            self.list_files(self.paths)

    def _run_cli_import(
        self, operation_option: Literal["copy", "move"] | None = None
    ) -> None:
        """Run the `import` CLI command."""
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
        """Run the `move` CLI command."""
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
        """Run the `modify` CLI command."""
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
        """Run the `update` CLI command."""
        update_items(
            lib=self.lib,
            query=query,
            album=album,
            move=move,
            pretend=pretend,
            fields=fields,
        )
