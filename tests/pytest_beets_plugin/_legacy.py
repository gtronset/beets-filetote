"""Legacy unittest-based test case for beets-filetote.

Deprecated: migrate tests to use the ``beets_plugin_env`` fixture instead.
This file should be deleted once all tests are migrated.
"""

# ruff: noqa: SLF001

import logging
import os
import shutil
import tempfile
import unittest

from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from beets import config, library, plugins, util
from beets.importer import ImportSession

from ._io import DummyIO
from .assertions import BeetsAssertions
from .media import MediaCreator, MediaSetup
from .plugin_lifecycle import (
    _activate_plugins,
    _clear_plugin_state,
    _deactivate_plugins,
)

# TODO(gtronset): Remove this once beets 2.4 and 2.5 are no longer supported (the old
# fallback import paths can be removed).
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

if TYPE_CHECKING:
    from mediafile import MediaFile


log = logging.getLogger("beets")


class TestCase(unittest.TestCase):
    """A unittest.TestCase subclass that saves and restores beets'
    global configuration.

    Deprecated: migrate tests to use the ``beets_plugin_env`` fixture instead.
    """

    def setUp(self) -> None:
        # A "clean" source list including only the defaults.
        config.sources = []
        config.read(user=False, defaults=True)

        # Direct paths to a temporary directory. Tests can also use this
        # temporary directory.
        self.temp_dir = Path(tempfile.mkdtemp())

        config["statefile"] = str(self.temp_dir / "state.pickle")
        config["library"] = str(self.temp_dir / "library.db")
        config["directory"] = str(self.temp_dir / "libdir")

        # Set $HOME, which is used by confit's `config_dir()` to create
        # directories.
        self._old_home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.temp_dir)

        # Initialize, but don't install, a DummyIO.
        self.in_out = DummyIO()


class FiletoteTestCase(TestCase, BeetsAssertions, MediaCreator):
    """Legacy unittest-based test case for beets-filetote.

    Deprecated: migrate tests to use the ``beets_plugin_env`` fixture instead.

    Provides common setup and teardown, a convenience method for exercising the
    plugin/importer, tools to setup a library, a directory containing files
    that are to be imported and an import session. The class also provides stubs
    for the autotagging library and assertions helpers.
    """

    def setUp(self, other_plugins: list[str] | None = None) -> None:
        super().setUp()

        other_plugins = other_plugins or []
        self.plugins = other_plugins

        self.lib_dir: Path = self.temp_dir / "testlib_dir"
        self.lib: library.Library = self._create_library(self.lib_dir)

        self.rsrc_mp3: str = "full.mp3"
        self._media_count: int = 0
        self._pairs_count: int = 0

        self.import_dir: Path = self.temp_dir / "import_dir"
        self.import_media: list[MediaFile] | None = None
        self.importer: ImportSession | None = None
        self.paths: Path | None = None

        self.in_out.install()

    def _create_library(self, lib_dir: Path) -> library.Library:
        lib_db = self.temp_dir / "testlib.blb"
        lib_dir.mkdir(parents=True, exist_ok=True)

        lib = library.Library(util.bytestring_path(lib_db))
        lib.directory = util.bytestring_path(lib_dir)
        lib.path_formats = [
            ("default", self.fmt_path("$artist", "$album", "$title")),
            ("singleton:true", self.fmt_path("singletons", "$title")),
            ("comp:true", self.fmt_path("compilations", "$album", "$title")),
        ]
        return lib

    def tearDown(self) -> None:
        _deactivate_plugins()
        _clear_plugin_state()

        self.lib._close()
        super().tearDown()

    def _run_cli_command(
        self,
        command: Literal["import", "modify", "move", "update"],
        **kwargs: Any,
    ) -> None:
        """Create an instance of the plugin, run the supplied command, and
        remove/unregister the plugin instance so a new instance can
        be created when this method is run again.
        This is a convenience method that can be called to set-up, exercise,
        and tear-down the system under test after setting any config options
        and before assertions are made regarding changes to the filesystem.
        """
        log_string = f"Running CLI: {command}"
        log.debug(log_string)

        _activate_plugins(self.plugins)

        # Get the function associated with the provided command name and run it with the
        # provided kwargs.
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
        """Runs the "import" CLI command. This should be called with
        _run_cli_command().
        """
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
        """Runs the "move" CLI command. This should be called with
        _run_cli_command().
        """
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
        """Runs the "modify" CLI command. This should be called with
        _run_cli_command().
        """
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
        """Runs the "update" CLI command. This should be called with
        _run_cli_command().
        """
        update_items(
            lib=self.lib,
            query=query,
            album=album,
            move=move,
            pretend=pretend,
            fields=fields,
        )

    def _create_flat_import_dir(
        self,
        media_files: list[MediaSetup] | None = None,
        pair_subfolders: bool = False,
    ) -> None:
        """Creates a directory with media files and artifacts.
        Sets ``self.import_dir`` to the path of the directory. Also sets
        ``self.import_media`` to a list :class:`MediaFile` for all the media files in
        the directory.
        """
        if media_files is None:
            media_files = [MediaSetup(pair_subfolders=pair_subfolders)]

        self._set_import_dir()

        album_path: Path = self.import_dir / "the_album"
        album_path.mkdir(parents=True, exist_ok=True)

        for artifact in [
            "artifact.file",
            "artifact2.file",
            "artifact.nfo",
            "artifact.lrc",
        ]:
            self.create_file(album_path / artifact)

        media_file_count: int = 0
        media_list: list[MediaFile] = []

        for media_file in media_files:
            media_file_count += media_file.count
            media_list.extend(
                self.generate_paired_media_list(
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

    def _create_nested_import_dir(
        self,
        disc1_media_files: list[MediaSetup] | None = None,
        disc2_media_files: list[MediaSetup] | None = None,
    ) -> None:
        """Creates a directory with media files and artifacts nested in subdirectories.
        Sets ``self.import_dir`` to the path of the directory. Also sets
        ``self.import_media`` to a list :class:`MediaFile` for all the media files in
        the directory.
        """
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

        for artifact in [
            "artifact.file",
            "artifact2.file",
            "artifact_disc1.nfo",
        ]:
            self.create_file(disc1_path / artifact)

        for artifact in [
            "artifact3.file",
            "artifact4.file",
            "artifact_disc2.nfo",
        ]:
            self.create_file(disc2_path / artifact)

        media_file_count: int = 0
        media_list: list[MediaFile] = []

        for media_file in disc1_media_files:
            media_file_count += media_file.count
            media_list.extend(
                self.generate_paired_media_list(
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
                self.generate_paired_media_list(
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

    def _set_import_dir(self) -> None:
        self.import_dir = self.temp_dir / "testsrc_dir"
        if self.import_dir.is_dir():
            shutil.rmtree(self.import_dir)

    def _setup_import_session(  # noqa: PLR0913
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

        # ImportSession expects a list of bytestring path
        import_path: list[bytes] = (
            [util.bytestring_path(import_dir)] if import_dir else []
        )

        self.importer = ImportSession(
            self.lib,
            loghandler=None,
            paths=import_path,
            query=query,
        )
