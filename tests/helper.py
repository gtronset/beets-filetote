"""Helper functions for tests for the beets-filetote plugin."""
# ruff: noqa: SLF001

import contextlib
import importlib.util
import logging
import shutil
import sys
import types

from collections.abc import Generator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import beetsplug

from beets import config, library, plugins, util
from beets.importer import ImportSession
from beets.plugins import BeetsPlugin
from mediafile import MediaFile

from ._item_model import MediaMeta
from tests import _common

# TODO(gtronset): Remove this once beets 2.4 and 2.5 are no longer supported (the old
# fallback import paths can be removed).
# https://github.com/gtronset/beets-filetote/pull/253
try:
    from beets.ui.commands.modify import modify_items
    from beets.ui.commands.move import move_items
    from beets.ui.commands.update import update_items
except ImportError:
    from beets.ui.commands import modify_items, move_items, update_items

log = logging.getLogger("beets")

# Test resources path.
RSRC: Path = Path(__file__).resolve().parent / "rsrc"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
            msg = msg[:-5]
        self.messages.append(msg)


@contextlib.contextmanager
def capture_log_with_traceback(
    logger_name: str = "beets",
) -> Generator[list[str], None, None]:
    """A context manager to capture log messages, including tracebacks."""
    logger = logging.getLogger(logger_name)
    handler = ListLogHandler()
    logger.addHandler(handler)
    try:
        yield handler.messages
    finally:
        logger.removeHandler(handler)


def _load_module_from_path(module_name: str, module_path: str) -> types.ModuleType:
    """Core helper to load a module from a specific file path."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if not (spec and spec.loader):
        raise ImportError(
            f"Could not create module spec for {module_name} at {module_path}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def import_plugin_module_statically(module_name: str) -> types.ModuleType:
    """Load a plugin module directly from its source file.

    This is useful for unit tests that need to import a module statically,
    bypassing the `beetsplug` package namespace and avoiding contamination
    from integration tests that dynamically load plugins.
    """
    module_path: Path = PROJECT_ROOT / f"beetsplug/{module_name}.py"
    return _load_module_from_path(module_name, str(module_path))


def _import_local_plugin(
    module_path: Path, class_name: str, module_name: str
) -> type[BeetsPlugin]:
    """Dynamically import a plugin class from a local file."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    module: types.ModuleType = _load_module_from_path(module_name, str(module_path))

    # Patch beetsplug namespace if needed
    namespace, _, submodule = module_name.partition(".")
    if namespace == "beetsplug" and submodule:
        setattr(beetsplug, submodule, module)
        sys.modules[f"beetsplug.{submodule}"] = module
    return cast("type[BeetsPlugin]", getattr(module, class_name))


@dataclass
class MediaSetup:
    """Setup config for to-be-created media files."""

    file_type: str = "mp3"
    count: int = 3
    generate_pair: bool = True
    pair_subfolders: bool = False


# More types may be expanded as testing becomes more sophisticated.
RSRC_TYPES = {
    "mp3": "full.mp3",
    "flac": "full.flac",
    "wav": "full.wav",
}


class Assertions(_common.AssertionsMixin):
    """Helper assertions for testing."""

    def __init__(self) -> None:
        """Sets up baseline variables."""
        self.lib_dir: Path | None = None
        self.import_dir: Path | None = None

    def _resolve_relative_path(self, root: Path, relative_path: str | Path) -> Path:
        """Joins a root path with a relative path, ensuring the input is actually
        relative.

        Prevents usage errors where passing an absolute path would silently discard the
        root.
        """
        path_obj = Path(relative_path)

        if path_obj.is_absolute():
            raise ValueError(f"Path must be relative, got absolute: {path_obj}")

        return root / path_obj

    def assert_in_lib_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path exists inside the library directory."""
        if self.lib_dir:
            self.assert_exists(self._resolve_relative_path(self.lib_dir, relative_path))

    def assert_not_in_lib_dir(self, relative_path: str | Path) -> None:
        """Asserts that the relative path does not exist inside the library
        directory.
        """
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
        """Asserts that the relative path does not exist inside the import directory."""
        if self.import_dir:
            self.assert_does_not_exist(
                self._resolve_relative_path(self.import_dir, relative_path)
            )

    def assert_islink(self, relative_path: str | Path) -> None:
        """Asserts that the relative path is a symbolic link inside the library
        directory.
        """
        if self.lib_dir:
            path = self._resolve_relative_path(self.lib_dir, relative_path)
            assert path.is_symlink(), f"Expected {path} to be a symbolic link"

    def assert_number_of_files_in_dir(self, count: int, directory: Path) -> None:
        """Assert that there are ``count`` files in the provided path."""
        # Verify it exists first to give a better error message
        assert directory.exists(), f"Directory does not exist: {directory}"
        assert directory.is_dir(), f"Path is not a directory: {directory}"

        actual_count = len(list(directory.iterdir()))
        assert actual_count == count, (
            f"Expected {count} files in {directory}, found {actual_count}"
        )


class HelperUtils:
    """Helpful utilities for testing the plugin's actions."""

    def _log_indenter(self, indent_level: int) -> str:
        return " " * 4 * (indent_level)

    def fmt_path(self, *parts: str) -> str:
        """Joins path components into a string using the current OS separator.

        Useful for defining Beets path_formats without using os.path.join.
        """
        return str(Path(*parts))

    def create_file(self, path: Path) -> None:
        """Creates a file in a specific location, ensuring the parent directories
        exist.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

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
                # Should not happen if walking inside valid startpath
                level = 0

            indent = self._log_indenter(level)
            log_string = f"{indent}{root_path.name}/"
            log.debug(log_string)

            subindent = self._log_indenter(level + 1)
            for filename in files:
                sub_log_string = f"{subindent}{util.displayable_path(filename)}"
                log.debug(sub_log_string)

    def get_rsrc_from_extension(self, file_ext: str) -> str:
        """Gets the actual file matching extension if available, otherwise
        default to MP3.
        """
        file_type = file_ext.lstrip(".").lower()

        return RSRC_TYPES.get(file_type, RSRC_TYPES["mp3"])


class FiletoteTestCase(_common.TestCase, Assertions, HelperUtils):
    """Provides common setup and teardown, a convenience method for exercising the
    plugin/importer, tools to setup a library, a directory containing files
    that are to be imported and an import session. The class also provides stubs
    for the autotagging library and assertions helpers.
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

        # Install the DummyIO to capture anything directed to stdout
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
                # If the module or attribute doesn't exist, skip it.
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

        # Always load local Filetote
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
                raise AssertionError(f"Attempt to load unknown plugin: {other_plugin}")

        plugins._classes = set(plugin_class_list)
        config["plugins"] = plugin_list

        plugins.load_plugins()

    def unload_plugins(self) -> None:
        """Unload all plugins and remove the from the configuration."""
        config["plugins"] = []

        if plugins._instances:
            classes = list(plugins._classes)

            # In case `audible` or another plugin is included, iterate through
            # each plugin class.
            for plugin_class in classes:
                # Unregister listeners if they exist for the plugin
                if plugin_class.listeners:
                    for event in list(plugin_class.listeners):
                        plugin_class.listeners[event].clear()

                instances = plugins._instances
                plugins._instances = [
                    inst for inst in instances if not isinstance(inst, plugin_class)
                ]

        for modname in list(sys.modules):
            if modname.startswith("beetsplug.filetote") or modname.startswith(
                "beetsplug.audible"
            ):
                del sys.modules[modname]

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

        self.load_plugins(self.plugins)

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

        album_path: Path = self.import_dir / "the_album"
        album_path.mkdir(parents=True, exist_ok=True)

        # Create artifacts
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

        # Number of desired media
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

        album_path: Path = self.import_dir / "the_album"
        disc1_path: Path = album_path / "disc1"
        disc2_path: Path = album_path / "disc2"

        disc1_path.mkdir(parents=True)
        disc2_path.mkdir(parents=True)

        # Create Disc1 artifacts
        disc1_artifacts = [
            "artifact.file",
            "artifact2.file",
            "artifact_disc1.nfo",
        ]

        for artifact in disc1_artifacts:
            self.create_file(disc1_path / artifact)

        # Create Disc2 artifacts
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
        album_path: Path,
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
            media_path = album_path / f"{trackname}.{file_type}"

            media_list.append(
                self.create_medium(
                    path=media_path,
                    media_meta=MediaMeta(
                        title=f"{title_prefix}{count}", track=count, disc=disc
                    ),
                )
            )
            count -= 1

            if generate_pair:
                # Create paired artifact
                pair_path: Path = album_path

                if pair_subfolders:
                    pair_path = album_path / "lyrics" / "lyric-subfolder"

                pair_path.mkdir(parents=True, exist_ok=True)
                self.create_file(pair_path / f"{trackname}.lrc")

        return media_list

    def create_medium(
        self, path: Path, media_meta: MediaMeta | None = None
    ) -> MediaFile:
        """Creates and saves a media file object located at path using resource_name
        from the beets test resources directory as initial data.

        The file type is inferred from the file extension (e.g. `.mp3` -> full.mp3).
        Defaults to mp3 if unknown.
        """
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
        """Updates the metadata of an existing media file object located at path."""
        medium = MediaFile(str(path))

        for item, value in meta_updates.items():
            setattr(medium, item, value)
        medium.save()

    def _set_import_dir(self) -> None:
        """Sets the import_dir and ensures that it is empty."""
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
