"""Utility classes and functions for beets plugin tests."""

# ruff: noqa: SLF001

# from __future__ import annotations

import contextlib
import importlib.util
import logging
import shutil
import sys

from collections.abc import Generator
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Literal, TypeAlias, cast

import beetsplug

from beets import config, library, plugins, util
from beets.importer import ImportSession
from beets.plugins import BeetsPlugin
from mediafile import MediaFile

from .. import _common
from ._item_model import MediaMeta
from .assertions import BeetsAssertions

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


# beets uses the standard Python logging levels (integers)
LogLevels: TypeAlias = Literal[
    10,  # logging.DEBUG
    20,  # logging.INFO
    30,  # logging.WARNING
    40,  # logging.ERROR
    50,  # logging.CRITICAL
]

log = logging.getLogger("beets")

# Test resources path.
RSRC: Path = Path(__file__).resolve().parents[1] / "rsrc"
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# More types may be expanded as testing becomes more sophisticated.
RSRC_TYPES: dict[str, str] = {
    "mp3": "full.mp3",
    "flac": "full.flac",
    "wav": "full.wav",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MediaSetup:
    """Configuration for media files to create in an import directory."""

    file_type: str = "mp3"
    count: int = 3
    generate_pair: bool = True
    pair_subfolders: bool = False


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------


class ListLogHandler(logging.Handler):
    """A logging handler that records messages in a list, including tracebacks."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the handler and its message list."""
        super().__init__(*args, **kwargs)
        self.messages: list[str] = []
        self.setFormatter(logging.Formatter("%(message)s\n%(exc_text)s"))

    def emit(self, record: logging.LogRecord) -> None:
        """Appends the formatted log record to the message list."""
        msg = self.format(record)
        # The formatter adds "\nNone" for records without exceptions. Strip it.
        if msg.endswith("\nNone"):
            msg = msg.removesuffix("\nNone")
        self.messages.append(msg)


@contextlib.contextmanager
def capture_beets_log(
    logger_name: str = "beets",
    level: LogLevels = logging.DEBUG,
) -> Generator[list[str], None, None]:
    """A context manager to capture log messages, including tracebacks.

    Usage::

        with capture_beets_log("beets.filetote") as logs:
            do_something()
        assert any("expected message" in line for line in logs)
    """
    logger = logging.getLogger(logger_name)

    original_logger_level = logger.level
    original_verbose = config["verbose"].get()

    if level <= logging.DEBUG:
        required_verbosity = 2
    elif level <= logging.INFO:
        required_verbosity = 1
    else:
        required_verbosity = 0

    config["verbose"] = required_verbosity
    logger.setLevel(level)

    handler = ListLogHandler()
    logger.addHandler(handler)

    try:
        yield handler.messages
    finally:
        logger.removeHandler(handler)
        logger.setLevel(original_logger_level)
        config["verbose"] = original_verbose


# Backward-compatible alias
capture_log_with_traceback = capture_beets_log


# ---------------------------------------------------------------------------
# Plugin loading utilities
# ---------------------------------------------------------------------------


def _load_module_from_path(module_name: str, module_path: str | Path) -> ModuleType:
    """Core helper to load a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    if not (spec and spec.loader):
        msg = f"Could not create module spec for {module_name} at {module_path}"
        raise ImportError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def import_plugin_module_statically(module_name: str) -> ModuleType:
    """Load a plugin module directly from its source file.

    This is useful for unit tests that need to import a module statically,
    bypassing the ``beetsplug`` package namespace and avoiding contamination
    from integration tests that dynamically load plugins.
    """
    module_path: Path = PROJECT_ROOT / f"beetsplug/{module_name}.py"
    return _load_module_from_path(module_name, module_path)


def _import_local_plugin(
    module_path: Path,
    class_name: str,
    module_name: str,
) -> type[BeetsPlugin]:
    """Dynamically import a plugin class from a local file."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    module: ModuleType = _load_module_from_path(module_name, module_path)

    # Patch beetsplug namespace if needed
    namespace, _, submodule = module_name.partition(".")
    if namespace == "beetsplug" and submodule:
        setattr(beetsplug, submodule, module)
        sys.modules[f"beetsplug.{submodule}"] = module
    return cast("type[BeetsPlugin]", getattr(module, class_name))


# ---------------------------------------------------------------------------
# BeetsTestUtils
# ---------------------------------------------------------------------------


class BeetsTestUtils:
    """Utility methods for beets plugin tests."""

    def _log_indenter(self, indent_level: int) -> str:
        return " " * 4 * indent_level

    def fmt_path(self, *parts: str) -> str:
        """Joins path components into a string using the current OS separator."""
        return str(Path(*parts))

    def create_file(self, path: Path) -> None:
        """Creates a file, ensuring parent directories exist."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def delete_file(self, path: Path) -> None:
        """Deletes a file at a specific location, if it exists."""
        if path.exists():
            path.unlink()

    def list_files(self, startpath: Path) -> None:
        """Provide a formatted list of files, directories, and their contents."""
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
        """Gets the actual file matching extension, defaulting to MP3."""
        file_type = file_ext.lstrip(".").lower()
        return RSRC_TYPES.get(file_type, RSRC_TYPES["mp3"])


# Backward-compatible alias
HelperUtils = BeetsTestUtils


# ---------------------------------------------------------------------------
# Assertions (legacy class-based, for FiletoteTestCase)
# ---------------------------------------------------------------------------


class Assertions(BeetsAssertions):
    """Helper assertions for testing.

    Deprecated: use ``BeetsPluginFixture`` assertion methods instead.
    """

    def __init__(self) -> None:
        """Sets up baseline variables."""
        self.lib_dir: Path | None = None
        self.import_dir: Path | None = None

    def _resolve_relative_path(self, root: Path, relative_path: str | Path) -> Path:
        path_obj = Path(relative_path)
        if path_obj.is_absolute():
            msg = f"Path must be relative, got absolute: {path_obj}"
            raise ValueError(msg)
        return root / path_obj

    def assert_in_lib_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path exists inside the library directory."""
        if self.lib_dir:
            self.assert_exists(self._resolve_relative_path(self.lib_dir, relative_path))

    def assert_not_in_lib_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path does not exist inside the library dir."""
        if self.lib_dir:
            self.assert_does_not_exist(
                self._resolve_relative_path(self.lib_dir, relative_path)
            )

    def assert_import_dir_exists(self, import_dir: Path | None = None) -> None:
        """Asserts that the import directory exists."""
        directory = import_dir or self.import_dir
        if directory:
            self.assert_exists(directory)

    def assert_in_import_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path exists inside the import directory."""
        if self.import_dir:
            self.assert_exists(
                self._resolve_relative_path(self.import_dir, relative_path)
            )

    def assert_not_in_import_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path does not exist inside the import dir."""
        if self.import_dir:
            self.assert_does_not_exist(
                self._resolve_relative_path(self.import_dir, relative_path)
            )

    def assert_islink(self, relative_path: str | Path) -> None:
        """Asserts that the relative path is a symbolic link."""
        if self.lib_dir:
            path = self._resolve_relative_path(self.lib_dir, relative_path)
            assert path.is_symlink(), f"Expected {path} to be a symbolic link"

    def assert_number_of_files_in_dir(self, count: int, directory: Path) -> None:
        """Assert that there are ``count`` files in the provided path."""
        assert directory.exists(), f"Directory does not exist: {directory}"
        assert directory.is_dir(), f"Path is not a directory: {directory}"
        actual_count = len(list(directory.iterdir()))
        assert actual_count == count, (
            f"Expected {count} files in {directory}, found {actual_count}"
        )


# ---------------------------------------------------------------------------
# FiletoteTestCase (legacy unittest-based)
# ---------------------------------------------------------------------------


class FiletoteTestCase(_common.TestCase, Assertions, BeetsTestUtils):
    """Legacy unittest-based test case for beets-filetote.

    Deprecated: migrate tests to use the ``beets_plugin_env`` fixture instead.
    """

    def setUp(self, other_plugins: list[str] | None = None) -> None:
        """Handles all setup for testing, including library (database)."""
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
        """Cleans up and closes the library connection."""
        self.unload_plugins()

        attrs_to_clear = [
            ("plugins", "_instances"),
            ("plugins", "_classes"),
            ("plugins", "_event_listeners"),
            ("plugins.BeetsPlugin", "listeners"),
            ("plugins.BeetsPlugin", "_raw_listeners"),
        ]

        for obj_path, attr in attrs_to_clear:
            try:
                if "." in obj_path:
                    module_path, class_name = obj_path.rsplit(".", 1)
                    module = sys.modules[module_path]
                    obj = getattr(module, class_name)
                else:
                    obj = sys.modules[obj_path]
            except (KeyError, AttributeError):
                log.warning(f"Could not resolve path `{obj_path}` for teardown.")
                continue

            if hasattr(obj, attr):
                val = getattr(obj, attr)
                if val is not None and hasattr(val, "clear"):
                    val.clear()

        self.lib._close()
        super().tearDown()

    def load_plugins(self, other_plugins: list[str]) -> None:
        """Loads and sets up the plugin(s) for the test module."""
        plugin_list: list[str] = ["filetote"]
        plugin_class_list: list[Any] = []

        filetote_path = PROJECT_ROOT / "beetsplug/filetote.py"
        filetote_class = _import_local_plugin(
            filetote_path, "FiletotePlugin", "beetsplug.filetote"
        )
        plugin_class_list.append(filetote_class)

        stub_map = {
            "audible": ("tests/stubs/audible.py", "Audible"),
            "convert": ("tests/stubs/convert.py", "ConvertPlugin"),
            "inline": ("tests/stubs/inline.py", "InlinePlugin"),
        }

        for other_plugin in other_plugins:
            if other_plugin in stub_map:
                stub_path, class_name = stub_map[other_plugin]
                abs_stub_path = PROJECT_ROOT / stub_path
                plugin_class = _import_local_plugin(
                    abs_stub_path, class_name, f"beetsplug.{other_plugin}"
                )
                plugin_class_list.append(plugin_class)
                plugin_list.append(other_plugin)
            else:
                msg = f"Attempt to load unknown plugin: {other_plugin}"
                raise AssertionError(msg)

        plugins._classes = set(plugin_class_list)
        config["plugins"] = plugin_list
        plugins.load_plugins()

    def unload_plugins(self) -> None:
        """Unload all plugins and clean up global state."""
        config["plugins"] = []

        if plugins._instances:
            classes = list(plugins._classes)
            for plugin_class in classes:
                if plugin_class.listeners:
                    for event in list(plugin_class.listeners):
                        plugin_class.listeners[event].clear()
                instances = plugins._instances
                plugins._instances = [
                    inst for inst in instances if not isinstance(inst, plugin_class)
                ]

        for modname in list(sys.modules):
            if modname.startswith(("beetsplug.filetote", "beetsplug.audible")):
                del sys.modules[modname]

    def _run_cli_command(
        self,
        command: Literal["import", "modify", "move", "update"],
        **kwargs: Any,
    ) -> None:
        log_string = f"Running CLI: {command}"
        log.debug(log_string)

        self.load_plugins(self.plugins)

        command_func = getattr(self, f"_run_cli_{command}")
        command_func(**kwargs)

        plugins.send("cli_exit", lib=self.lib)
        self.unload_plugins()

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

    def _create_flat_import_dir(
        self,
        media_files: list[MediaSetup] | None = None,
        pair_subfolders: bool = False,
    ) -> None:
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

    def _create_nested_import_dir(
        self,
        disc1_media_files: list[MediaSetup] | None = None,
        disc2_media_files: list[MediaSetup] | None = None,
    ) -> None:
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

        for artifact in ["artifact.file", "artifact2.file", "artifact_disc1.nfo"]:
            self.create_file(disc1_path / artifact)

        for artifact in ["artifact3.file", "artifact4.file", "artifact_disc2.nfo"]:
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

        import_path: list[bytes] = (
            [util.bytestring_path(import_dir)] if import_dir else []
        )

        self.importer = ImportSession(
            self.lib,
            loghandler=None,
            paths=import_path,
            query=query,
        )
