"""Helper functions for tests for the beets-filetote plugin."""

# ruff: noqa: SLF001
from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, cast

from beets import config, library, plugins, util
from beets.importer import ImportSession
from beets.ui import commands
from mediafile import MediaFile

from ._item_model import MediaMeta
from tests import _common

if TYPE_CHECKING:
    from collections.abc import Iterator


log = logging.getLogger("beets")


def _prepare_local_beetsplug_namespace() -> None:
    """Make the repo-local `beetsplug/` importable and ensure it's used for
    subsequent `import beetsplug.*` calls.
    """
    root = Path(__file__).resolve().parents[1]  # project root
    # Ensure the project root is importable (so `beetsplug` resolves to this repo).
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Point the beetsplug namespace to the local package dir.
    import beetsplug as _bp  # noqa: PLC0415

    _bp.__path__ = [str(root / "beetsplug")]  # must be set before submodule imports


class LogCapture(logging.Handler):
    """Provides the ability to capture logs within tests."""

    def __init__(self) -> None:
        """Log handler init."""
        logging.Handler.__init__(self)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Emits a log message."""
        self.messages.append(str(record.msg))


@contextmanager
def capture_log(logger: str = "beets") -> Iterator[list[str]]:
    """Adds handler to capture beets' logs."""
    capture = LogCapture()
    logs = logging.getLogger(logger)
    logs.addHandler(capture)
    try:
        yield capture.messages
    finally:
        logs.removeHandler(capture)


@dataclass
class MediaSetup:
    """Setup config for to-be-created media files."""

    file_type: str = "mp3"
    count: int = 3
    generate_pair: bool = True
    pair_subfolders: bool = False


# More types may be expanded as testing becomes more sophisticated.
RSRC_TYPES = {
    "mp3": b"full.mp3",
    # "aac": b"full.aac",
    # "alac": b"full.alac",
    # "alac.m4a": b"full.alac.m4a",
    # "ogg": b"full.ogg",
    # "opus": b"full.opus",
    "flac": b"full.flac",
    # "ape": b"full.ape",
    # "wv": b"full.wv",
    # "mpc": b"full.mpc",
    # "m4a": b"full.m4a",
    # "asf": b"full.asf",
    # "aiff": b"full.aiff",
    # "dsf": b"full.dsf",
    "wav": b"full.wav",
    # "wave": b"full.wave",
    # "wma": b"full.wma",
}

if _common.HAVE_HARDLINK:
    # Some CI filesystems (overlayfs, tmpfs, split mounts) report
    # hardlink support but raise EXDEV when linking across temp
    # directories. This probe ensures the hardlink-specific test only
    # runs when the underlying platform can actually support the request.
    try:
        _probe_root = util.bytestring_path(tempfile.mkdtemp())
        try:
            _src_dir = os.path.join(_probe_root, b"src")
            _dst_dir = os.path.join(_probe_root, b"dst")
            os.makedirs(_src_dir)
            os.makedirs(_dst_dir)
            _src = os.path.join(_src_dir, b"probe_src")
            _dst = os.path.join(_dst_dir, b"probe_dst")
            with open(_src, "wb") as _handle:
                _handle.write(b"\x00")
            os.link(util.syspath(_src), util.syspath(_dst))
        finally:
            shutil.rmtree(_probe_root)
    except OSError:
        _common.HAVE_HARDLINK = False


class Assertions(_common.AssertionsMixin):
    """Helper assertions for testing."""

    def __init__(self) -> None:
        """Sets up baseline variables."""
        self.lib_dir: Optional[bytes] = None
        self.import_dir: Optional[bytes] = None

    def assert_in_lib_dir(self, *segments: bytes) -> None:
        """Join the ``segments`` and assert that this path exists in the library
        directory.
        """
        if self.lib_dir:
            self.assert_exists(os.path.join(self.lib_dir, *segments))

    def assert_not_in_lib_dir(self, *segments: bytes) -> None:
        """Join the ``segments`` and assert that this path does not exist in
        the library directory.
        """
        if self.lib_dir:
            self.assert_does_not_exist(os.path.join(self.lib_dir, *segments))

    def assert_import_dir_exists(self, import_dir: Optional[bytes] = None) -> None:
        """Asserts that the import directory exists."""
        directory = import_dir or self.import_dir
        if directory:
            self.assert_exists(directory)

    def assert_in_import_dir(self, *segments: bytes) -> None:
        """Join the ``segments`` and assert that this path exists in the import
        directory.
        """
        if self.import_dir:
            self.assert_exists(os.path.join(self.import_dir, *segments))

    def assert_not_in_import_dir(self, *segments: bytes) -> None:
        """Join the ``segments`` and assert that this path does not exist in
        the library directory.
        """
        if self.import_dir:
            self.assert_does_not_exist(os.path.join(self.import_dir, *segments))

    def assert_islink(self, *segments: bytes) -> None:
        """Join the ``segments`` with the `lib_dir` and assert that this path is a
        link.
        """
        if self.lib_dir:
            assert os.path.islink(os.path.join(self.lib_dir, *segments))

    def assert_equal_path(self, path_a: bytes, path_b: bytes) -> None:
        """Check that two paths are equal."""
        assert util.normpath(path_a) == util.normpath(path_b), (
            f"paths are not equal: {path_a!r} and {path_b!r}"
        )

    def assert_number_of_files_in_dir(self, count: int, *segments: bytes) -> None:
        """Assert that there are ``count`` files in path formed by joining
        ``segments``.
        """
        assert len(list(os.listdir(os.path.join(*segments)))) == count


class HelperUtils:
    """Helpful utilities for testing the plugin's actions."""

    def _log_indenter(self, indent_level: int) -> str:
        return " " * 4 * (indent_level)

    def create_file(self, path: bytes, filename: bytes) -> None:
        """Creates a file in a specific location."""
        with open(
            os.path.join(path, filename), mode="a", encoding="utf-8"
        ) as file_handle:
            file_handle.close()

    def list_files(self, startpath: bytes) -> None:
        """Provide a formatted list of files, directories, and their contents in
        logs.
        """
        path = startpath.decode("utf8")
        for root, _dirs, files in os.walk(path):
            level = root.replace(path, "").count(os.sep)

            indent = self._log_indenter(level)
            log_string = f"{indent}{os.path.basename(root)}/"
            log.debug(log_string)

            subindent = self._log_indenter(level + 1)
            for filename in files:
                sub_log_string = f"{subindent}{filename}"
                log.debug(sub_log_string)

    def get_rsrc_from_file_type(self, filetype: str) -> bytes:
        """Gets the actual file matching extension if available, otherwise
        default to MP3.
        """
        return RSRC_TYPES.get(filetype, RSRC_TYPES["mp3"])


class FiletoteTestCase(_common.TestCase, Assertions, HelperUtils):
    """Provides common setup and teardown, a convenience method for exercising the
    plugin/importer, tools to setup a library, a directory containing files
    that are to be imported and an import session. The class also provides stubs
    for the autotagging library and assertions helpers.
    """

    def setUp(self, other_plugins: Optional[list[str]] = None) -> None:
        """Handles all setup for testing, including library (database)."""
        super().setUp()

        other_plugins = other_plugins or []

        self.load_plugins(other_plugins)

        self.lib_dir: bytes = os.path.join(self.temp_dir, b"testlib_dir")

        self.lib: library.Library = self._create_library(self.lib_dir)

        self.rsrc_mp3: bytes = b"full.mp3"

        self._media_count: int = 0
        self._pairs_count: int = 0

        self.import_dir: bytes = b""
        self.import_media: Optional[list[MediaFile]] = None
        self.importer: Optional[ImportSession] = None
        self.paths: Optional[bytes] = None

        # Install the DummyIO to capture anything directed to stdout
        self.in_out.install()

    def _create_library(self, lib_dir: bytes) -> library.Library:
        lib_db = os.path.join(self.temp_dir, b"testlib.blb")

        os.mkdir(lib_dir)

        lib = library.Library(lib_db)
        lib.directory = lib_dir

        lib.path_formats = [
            ("default", os.path.join("$artist", "$album", "$title")),
            ("singleton:true", os.path.join("singletons", "$title")),
            ("comp:true", os.path.join("compilations", "$album", "$title")),
        ]

        return lib

    def tearDown(self) -> None:
        """Cleans up and closes the library connection."""
        self.lib._close()
        super().tearDown()

    def load_plugins(self, other_plugins: list[str] | None = None) -> None:
        """Load only the plugins explicitly requested for this test,
        from the repo-local tree.
        """
        import importlib  # noqa: PLC0415
        import tempfile  # noqa: PLC0415

        other_plugins = other_plugins or []
        self._active_plugins = ["filetote", *other_plugins]

        # Hard-reset config/state
        config.clear()
        cast("Any", config)._add_default_source()
        # Newer Beets releases access `config["verbose"]` during pluginload;
        # provide the default value since `config.clear()` removes it.
        config["verbose"].set(0)
        os.environ["BEETSDIR"] = tempfile.mkdtemp(prefix="beets-test-")
        config["pluginpath"] = []  # don't search extra paths

        # Prepare local namespace before any submodule imports
        _prepare_local_beetsplug_namespace()

        # Import only the plugins we actually need
        filetote_mod = importlib.import_module("beetsplug.filetote")

        approved_map = {
            "inline": "beetsplug.inline",
            "convert": "beetsplug.convert",
            "audible": "beetsplug.audible",
        }
        imported: dict[str, Any] = {}
        for name in other_plugins:
            if name not in approved_map:
                raise AssertionError(f"Attempt to load unknown plugin: {name}")
            imported[name] = importlib.import_module(approved_map[name])

        # Reset registries to avoid cross-test listener leaks
        plugins._instances.clear()
        if hasattr(plugins, "_classes"):
            plugins._classes.clear()
        if hasattr(plugins, "_event_listeners"):
            plugins._event_listeners.clear()
        if hasattr(plugins.BeetsPlugin, "listeners"):
            plugins.BeetsPlugin.listeners.clear()
        if hasattr(plugins.BeetsPlugin, "_raw_listeners"):
            plugins.BeetsPlugin._raw_listeners.clear()

        # Register exactly the plugin classes we want available
        plugin_class_list = [filetote_mod.FiletotePlugin]
        if "inline" in imported:
            plugin_class_list.append(imported["inline"].InlinePlugin)
        if "convert" in imported:
            plugin_class_list.append(imported["convert"].ConvertPlugin)
        if "audible" in imported:
            plugin_class_list.append(imported["audible"].Audible)
        if hasattr(plugins, "_classes"):
            plugins._classes = set(plugin_class_list)

        # Configure names to load; new Beets reads from config["plugins"]
        config["plugins"] = self._active_plugins

        # Set safe defaults before loading audible if requested
        if "audible" in imported:
            config["audible"]["write_description_file"].set(False)
            config["audible"]["write_narrator_file"].set(False)

        plugins.load_plugins()

    def unload_plugins(self) -> None:
        """Unload all plugins and clear Beets plugin registry safely."""
        config["plugins"] = []

        plugins._instances.clear()
        if hasattr(plugins, "_classes"):
            plugins._classes.clear()

        if hasattr(plugins, "_event_listeners"):
            plugins._event_listeners.clear()
        if hasattr(plugins.BeetsPlugin, "listeners"):
            plugins.BeetsPlugin.listeners.clear()
        if hasattr(plugins.BeetsPlugin, "_raw_listeners"):
            plugins.BeetsPlugin._raw_listeners.clear()

    def _run_cli_command(
        self, command: Literal["import", "modify", "move", "update"], **kwargs: Any
    ) -> None:
        """Create an instance of the plugin, run the supplied command, and
        remove/unregister the plugin instance so a new instance can
        be created when this method is run again.

        This is a convenience method that can be called to setup, exercise
        and teardown the system under test after setting any config options
        and before assertions are made regarding changes to the filesystem.
        """
        log_string = f"Running CLI: {command}"
        log.debug(log_string)

        if hasattr(self, "_active_plugins"):
            config["plugins"] = self._active_plugins

        plugins.load_plugins()
        plugins.send("pluginload")

        # Get the function associated with the provided command name
        command_func = getattr(self, f"_run_cli_{command}")

        # Call the function with the provided arguments
        command_func(**kwargs)

        plugins.send("cli_exit", lib=self.lib)
        self.unload_plugins()

        log.debug("--- library structure")
        self.list_files(self.lib_dir)

        if self.paths:
            log.debug("--- source structure after import")
            self.list_files(self.paths)

    def _run_cli_import(
        self, operation_option: Optional[Literal["copy", "move"]] = None
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
        dest_dir: Optional[bytes] = None,
        album: Optional[str] = None,
        copy: bool = False,
        pretend: bool = False,
        export: bool = False,
    ) -> None:
        """Runs the "move" CLI command. This should be called with
        _run_cli_command().
        """
        commands.move_items(
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
        mods: Optional[dict[str, str]] = None,
        dels: Optional[dict[str, str]] = None,
        write: bool = True,
        move: bool = True,
        album: Optional[str] = None,
    ) -> None:
        """Runs the "modify" CLI command. This should be called with
        _run_cli_command().
        """
        mods = mods or {}
        dels = dels or {}

        commands.modify_items(
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
        album: Optional[str] = None,
        move: bool = True,
        pretend: bool = False,
        fields: Optional[list[str]] = None,
    ) -> None:
        """Runs the "update" CLI command. This should be called with
        _run_cli_command().
        """
        commands.update_items(
            lib=self.lib,
            query=query,
            album=album,
            move=move,
            pretend=pretend,
            fields=fields,
        )

    def _create_flat_import_dir(
        self,
        media_files: Optional[list[MediaSetup]] = None,
        pair_subfolders: bool = False,
    ) -> None:
        """Creates a directory with media files and artifacts.
        Sets ``self.import_dir`` to the path of the directory. Also sets
        ``self.import_media`` to a list :class:`MediaFile` for all the media files in
        the directory.

        The directory has the following layout
            testsrc_dir/
                the_album/
                    track_1.mp3
                    track_2.mp3
                    track_3.mp3
                    artifact.file
                    artifact2.file
                    artifact.nfo
                    artifact.lrc
                    track_1.lrc
                    track_2.lrc
                    track_3.lrc
        """
        if media_files is None:
            media_files = [MediaSetup(pair_subfolders=pair_subfolders)]

        self._set_import_dir()

        if self.import_dir is None:
            return

        album_path = os.path.join(self.import_dir, b"the_album")
        os.makedirs(album_path)

        # Create artifacts
        artifacts = [
            b"artifact.file",
            b"artifact2.file",
            b"artifact.nfo",
            b"artifact.lrc",
        ]

        for artifact in artifacts:
            self.create_file(album_path, artifact)

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

        # Number of desired media
        self._media_count = self._pairs_count = media_file_count

        self.import_media = media_list

        log.debug("--- import directory created")
        self.list_files(self.import_dir)

    def _create_nested_import_dir(
        self,
        disc1_media_files: Optional[list[MediaSetup]] = None,
        disc2_media_files: Optional[list[MediaSetup]] = None,
    ) -> None:
        """Creates a directory with media files and artifacts nested in subdirectories.
        Sets ``self.import_dir`` to the path of the directory. Also sets
        ``self.import_media`` to a list :class:`MediaFile` for all the media files in
        the directory.

        The directory has the following layout
            the_album/
                disc1/
                    track_1.mp3
                    artifact1.file
                disc2/
                    track_1.mp3
                    artifact2.file
        """
        if disc1_media_files is None:
            disc1_media_files = [MediaSetup()]

        if disc2_media_files is None:
            disc2_media_files = [MediaSetup()]

        self._set_import_dir()

        if self.import_dir is None:
            return

        album_path = os.path.join(self.import_dir, b"the_album")
        disc1_path = os.path.join(album_path, b"disc1")
        disc2_path = os.path.join(album_path, b"disc2")

        os.makedirs(disc1_path)
        os.makedirs(disc2_path)

        # Create Disc1 artifacts
        disc1_artifacts = [
            b"artifact.file",
            b"artifact2.file",
            b"artifact_disc1.nfo",
        ]

        for artifact in disc1_artifacts:
            self.create_file(disc1_path, artifact)

        # Create Disc2 artifacts
        disc2_artifacts = [
            b"artifact3.file",
            b"artifact4.file",
            b"artifact_disc2.nfo",
        ]

        for artifact in disc2_artifacts:
            self.create_file(disc2_path, artifact)

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
                )
            )

        # Number of desired media
        self._pairs_count = media_file_count
        self._media_count = media_file_count

        self.import_media = media_list

        log.debug("--- import directory created")
        self.list_files(self.import_dir)

    def _generate_paired_media_list(  # noqa: PLR0913
        self,
        album_path: bytes,
        count: int = 3,
        generate_pair: bool = True,
        pair_subfolders: bool = False,
        filename_prefix: str = "track_",
        file_type: str = "mp3",
        title_prefix: str = "Tag Title ",
        disc: int = 1,
    ) -> list[MediaFile]:
        """Generates the desired number of media files and corresponding
        "paired" artifacts.
        """
        media_list: list[MediaFile] = []

        while count > 0:
            trackname = f"{filename_prefix}{count}"
            media_list.append(
                self._create_medium(
                    path=os.path.join(
                        album_path,
                        f"{trackname}.{file_type}".encode(),
                    ),
                    resource_name=self.get_rsrc_from_file_type(file_type),
                    media_meta=MediaMeta(
                        title=f"{title_prefix}{count}", track=count, disc=disc
                    ),
                )
            )
            count -= 1

            if generate_pair:
                # Create paired artifact
                pair_path = album_path

                if pair_subfolders:
                    pair_path = os.path.join(album_path, b"lyrics", b"lyric-subfolder")

                os.makedirs(pair_path, exist_ok=True)

                self.create_file(pair_path, f"{trackname}.lrc".encode())
        return media_list

    def _create_medium(
        self, path: bytes, resource_name: bytes, media_meta: Optional[MediaMeta] = None
    ) -> MediaFile:
        """Creates and saves a media file object located at path using resource_name
        from the beets test resources directory as initial data.
        """
        if media_meta is None:
            media_meta = MediaMeta()

        # Copy media file
        resource_path = os.path.join(_common.RSRC, resource_name)

        shutil.copy(resource_path, path)
        medium = MediaFile(path)

        for item, value in asdict(media_meta).items():
            setattr(medium, item, value)
        medium.save()

        return medium

    def _update_medium(self, path: bytes, meta_updates: dict[str, str]) -> None:
        medium = MediaFile(path)

        for item, value in meta_updates.items():
            setattr(medium, item, value)
        medium.save()

    def _set_import_dir(self) -> None:
        """Sets the import_dir and ensures that it is empty."""
        self.import_dir = os.path.join(self.temp_dir, b"testsrc_dir")
        if os.path.isdir(self.import_dir):
            shutil.rmtree(self.import_dir)
        self.import_dir = os.path.join(self.temp_dir, b"testsrc_dir")

    def _setup_import_session(  # noqa: PLR0913
        self,
        import_dir: Optional[bytes] = None,
        delete: bool = False,
        threaded: bool = False,
        copy: bool = True,
        singletons: bool = False,
        move: bool = False,
        autotag: bool = True,
        query: Optional[str] = None,
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

        import_path: list[bytes] = [import_dir] if import_dir else []

        self.importer = ImportSession(
            self.lib,
            loghandler=None,
            paths=import_path,
            query=query,
        )
