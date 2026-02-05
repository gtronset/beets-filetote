"""Helper functions for tests for the beets-filetote plugin."""
# ruff: noqa: SLF001

import contextlib
import importlib.util
import inspect
import logging
import os
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
from beets.ui.commands import modify as command_modify
from beets.ui.commands import move as command_move
from beets.ui.commands import update as command_update
from mediafile import MediaFile

from ._item_model import MediaMeta
from tests import _common

log = logging.getLogger("beets")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


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
    module_path = os.path.join(PROJECT_ROOT, f"beetsplug/{module_name}.py")

    return _load_module_from_path(module_name, module_path)


def _import_local_plugin(
    module_path: str, class_name: str, module_name: str
) -> type[BeetsPlugin]:
    """Dynamically import a plugin class from a local file."""
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    module = _load_module_from_path(module_name, module_path)

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


class Assertions(_common.AssertionsMixin):
    """Helper assertions for testing."""

    def __init__(self) -> None:
        """Sets up baseline variables."""
        self.lib_dir: bytes | None = None
        self.import_dir: bytes | None = None

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

    def assert_import_dir_exists(self, import_dir: bytes | None = None) -> None:
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

    def assert_halts_with_message(
        self, command: str, message: str, **kwargs: Any
    ) -> None:
        """Runs a CLI command and asserts that it halts, either by raising an
        AssertionError (older beets) or by logging an error (newer beets).
        """
        exception_caught = False

        # TODO(gtronset): Refactor once Beets v2.3 is no longer supported:
        # https://github.com/gtronset/beets-filetote/pull/231

        # We cannot use `pytest.raises` here because this test needs to handle
        # two valid outcomes: an exception being raised (older beets versions)
        # or an error being logged (newer beets versions).
        with capture_log_with_traceback() as logs:
            try:
                # The `self` here refers to the test case instance, which has this
                # method.
                self._run_cli_command(command, **kwargs)  # type: ignore[attr-defined]
            except AssertionError as e:
                # Older Beets versions might raise the exception.
                exception_caught = True
                assert message in str(e)  # noqa: PT017

        if not exception_caught:
            # Newer Beets versions swallow the exception and log it.
            log_text = "".join(logs)
            assert message in log_text, (
                f"The expected warning '{message}' was not logged."
            )


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

    def setUp(self, other_plugins: list[str] | None = None) -> None:
        """Handles all setup for testing, including library (database)."""
        super().setUp()

        other_plugins = other_plugins or []

        self.plugins = other_plugins

        self.lib_dir: bytes = os.path.join(self.temp_dir, b"testlib_dir")

        self.lib: library.Library = self._create_library(self.lib_dir)

        self.rsrc_mp3: bytes = b"full.mp3"

        self._media_count: int = 0
        self._pairs_count: int = 0

        self.import_dir: bytes = b""
        self.import_media: list[MediaFile] | None = None
        self.importer: ImportSession | None = None
        self.paths: bytes | None = None

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

        root = Path(__file__).resolve().parents[1]

        # Always load local Filetote
        filetote_path = os.path.abspath(os.path.join(root, "beetsplug", "filetote.py"))
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
                abs_stub_path = os.path.abspath(stub_path)

                plugin_class = _import_local_plugin(
                    abs_stub_path, class_name, f"beetsplug.{other_plugin}"
                )
                plugin_class_list.append(plugin_class)
                plugin_list.append(other_plugin)
            else:
                raise AssertionError(f"Attempt to load unknown plugin: {other_plugin}")

        plugins._classes = set(plugin_class_list)
        config["plugins"] = plugin_list

        # TODO(gtronset): Remove fallback once Beets v2.3 is no longer supported. Beets
        # 2.3 takes in a list of plugin names, while Beets 2.4+ does not take any
        # arguments:
        # https://github.com/gtronset/beets-filetote/pull/231
        load_plugins_sig = inspect.signature(plugins.load_plugins)
        if len(load_plugins_sig.parameters) == 1:
            plugins.load_plugins(plugin_list)
            plugins.send("pluginload")
        else:
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

                # TODO(gtronset): Remove fallback once Beets v2.3 is no longer
                # supported:
                # https://github.com/gtronset/beets-filetote/pull/231

                # Remove plugin instance(s) for both dict and list types
                instances = plugins._instances
                if isinstance(instances, dict):
                    # Beets 2.3: dict[type, instance]
                    if plugin_class in instances:
                        del instances[plugin_class]
                elif isinstance(instances, list):
                    # Beets 2.4+: list of instances
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
        command_move.move_items(
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

        command_modify.modify_items(
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
        command_update.update_items(
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
        self, path: bytes, resource_name: bytes, media_meta: MediaMeta | None = None
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
        import_dir: bytes | None = None,
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

        import_path: list[bytes] = [import_dir] if import_dir else []

        self.importer = ImportSession(
            self.lib,
            loghandler=None,
            paths=import_path,
            query=query,
        )
