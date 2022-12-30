import logging
import os
import shutil
from contextlib import contextmanager
from enum import Enum

import mediafile
from beets import config, importer, library, plugins, util

# Make sure the development versions of the plugins are used
import beetsplug  # noqa: E402
from beetsplug import filetote
from tests import _common

beetsplug.__path__ = [
    os.path.abspath(os.path.join(__file__, "..", "..", "beetsplug"))
]

log = logging.getLogger("beets")


class LogCapture(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.messages = []

    def emit(self, record):
        self.messages.append(str(record.msg))


@contextmanager
def capture_log(logger="beets"):
    capture = LogCapture()
    logs = logging.getLogger(logger)
    logs.addHandler(capture)
    try:
        yield capture.messages
    finally:
        logs.removeHandler(capture)


class FiletoteTestCase(_common.TestCase):
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=protected-access
    # pylint: disable=logging-fstring-interpolation
    """
    Provides common setup and teardown, a convenience method for exercising the
    plugin/importer, tools to setup a library, a directory containing files
    that are to be imported and an import session. The class also provides stubs
    for the autotagging library and assertions helpers.
    """

    def setUp(self):
        super().setUp()

        plugins._classes = set([filetote.FiletotePlugin])

        self._setup_library()

        self.rsrc_mp3 = b"full.mp3"

        self._media_count = None
        self._pairs_count = None

        self.import_dir = None
        self.import_media = None
        self.importer = None
        self.paths = None

        # Install the DummyIO to capture anything directed to stdout
        self.in_out.install()

    def _run_importer(self, operation_option=None):
        """
        Create an instance of the plugin, run the importer, and
        remove/unregister the plugin instance so a new instance can
        be created when this method is run again.
        This is a convenience method that can be called to setup, exercise
        and teardown the system under test after setting any config options
        and before assertions are made regarding changes to the filesystem.
        """
        # Setup
        # Create an instance of the plugin
        plugins.find_plugins()

        if operation_option == "copy":
            config["import"]["copy"] = True
            config["import"]["move"] = False
        elif operation_option == "move":
            config["import"]["copy"] = False
            config["import"]["move"] = True

        # Exercise
        # Run the importer
        self.importer.run()
        # Fake the occurrence of the cli_exit event
        plugins.send("cli_exit", lib=self.lib)

        # Teardown
        if plugins._instances:
            classes = list(plugins._classes)

            # Unregister listeners
            for event in classes[0].listeners:
                del classes[0].listeners[event][0]

            # Delete the plugin instance so a new one gets created for each test
            del plugins._instances[classes[0]]

        log.debug("--- library structure")
        self._list_files(self.lib_dir)

        log.debug("--- source structure after import")
        self._list_files(self.paths)

    def _setup_library(self):
        self.lib_db = os.path.join(self.temp_dir, b"testlib.blb")
        self.lib_dir = os.path.join(self.temp_dir, b"testlib_dir")

        os.mkdir(self.lib_dir)

        self.lib = library.Library(self.lib_db)
        self.lib.directory = self.lib_dir

        self.lib.path_formats = [
            ("default", os.path.join("$artist", "$album", "$title")),
            ("singleton:true", os.path.join("singletons", "$title")),
            ("comp:true", os.path.join("compilations", "$album", "$title")),
        ]

    def _create_file(self, album_path, filename):
        """Creates a file in a specific location."""
        with open(
            os.path.join(album_path, filename), mode="a", encoding="utf-8"
        ) as file_handle:
            file_handle.close()

    def _create_flat_import_dir(self, media_files=3, generate_pair=True):
        """
        Creates a directory with media files and artifacts.
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
        self._set_import_dir()

        album_path = os.path.join(self.import_dir, b"the_album")
        os.makedirs(album_path)

        # Create artifacts
        self._create_file(album_path, b"artifact.file")
        self._create_file(album_path, b"artifact2.file")
        self._create_file(album_path, b"artifact.nfo")
        self._create_file(album_path, b"artifact.lrc")

        # Number of desired media
        self._media_count = self._pairs_count = media_files

        media_list = self._generate_paired_media_list(
            album_path=album_path,
            count=self._media_count,
            generate_pair=generate_pair,
        )
        self.import_media = media_list

        log.debug("--- import directory created")
        self._list_files(self.import_dir)

    def _generate_paired_media_list(
        self, album_path, count, generate_pair=True
    ):
        """
        Generates the desired number of media files and corresponding
        "paired" artifacts.
        """
        media_list = []

        while count > 0:
            trackname = f"track_{count}"
            media_list.append(
                self._create_medium(
                    os.path.join(
                        album_path, f"{trackname}.mp3".encode("utf-8")
                    ),
                    self.rsrc_mp3,
                    track_name=f"Tag Title {count}",
                    track_number=count,
                )
            )
            count = count - 1

            if generate_pair:
                # Create paired artifact
                self._create_file(
                    album_path, f"{trackname}.lrc".encode("utf-8")
                )
        return media_list

    def _create_medium(
        self,
        path,
        resource_name,
        artist=None,
        album=None,
        albumartist=None,
        track_name=None,
        track_number=None,
    ):
        # pylint: disable=too-many-arguments
        """
        Creates and saves a media file object located at path using resource_name
        from the beets test resources directory as initial data
        """

        resource_path = os.path.join(_common.RSRC, resource_name)

        metadata = {
            "artist": artist or "Tag Artist",
            "album": album or "Tag Album",
            "albumartist": albumartist or "Tag Album Artist",
            "mb_trackid": None,
            "mb_albumid": None,
            "comp": None,
        }

        # Copy media file
        shutil.copy(resource_path, path)
        medium = mediafile.MediaFile(path)

        # Set metadata
        metadata["track"] = track_number or 1
        metadata["title"] = track_name or "Tag Title 1"
        for item, value in metadata.items():
            setattr(medium, item, value)
        medium.save()

        return medium

    def _set_import_dir(self):
        """
        Sets the import_dir and ensures that it is empty.
        """
        self.import_dir = os.path.join(self.temp_dir, b"testsrc_dir")
        if os.path.isdir(self.import_dir):
            shutil.rmtree(self.import_dir)
        self.import_dir = os.path.join(self.temp_dir, b"testsrc_dir")

    def _create_nested_import_dir(self):
        """
        Creates a directory with media files and artifacts nested in subdirectories.
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

    def _setup_import_session(
        self,
        import_dir=None,
        delete=False,
        threaded=False,
        copy=True,
        singletons=False,
        move=False,
        autotag=True,
    ):
        # pylint: disable=too-many-arguments

        config["import"]["copy"] = copy
        config["import"]["delete"] = delete
        config["import"]["timid"] = True
        config["threaded"] = threaded
        config["import"]["singletons"] = singletons
        config["import"]["move"] = move
        config["import"]["autotag"] = autotag
        config["import"]["resume"] = False

        self.paths = import_dir or self.import_dir

        self.importer = TestImportSession(
            self.lib,
            loghandler=None,
            paths=[import_dir or self.import_dir],
            query=None,
        )

    def _indenter(self, indent_level):
        return " " * 4 * (indent_level)

    def _list_files(self, startpath):
        path = startpath.decode("utf8")
        for root, _dirs, files in os.walk(path):
            level = root.replace(path, "").count(os.sep)
            indent = self._indenter(level)
            log.debug(f"{indent}{os.path.basename(root)}/")
            subindent = self._indenter(level + 1)
            for filename in files:
                log.debug(f"{subindent}{filename}")

    def assert_in_lib_dir(self, *segments):
        """
        Join the ``segments`` and assert that this path exists in the library
        directory
        """
        self.assert_exists(os.path.join(self.lib_dir, *segments))

    def assert_not_in_lib_dir(self, *segments):
        """
        Join the ``segments`` and assert that this path does not exist in
        the library directory
        """
        self.assert_does_not_exist(os.path.join(self.lib_dir, *segments))

    def assert_import_dir_exists(self, import_dir=None):
        """
        Join the ``segments`` and assert that this path exists in the import
        directory
        """
        directory = import_dir or self.import_dir
        self.assert_exists(directory)

    def assert_in_import_dir(self, *segments):
        """
        Join the ``segments`` and assert that this path exists in the import
        directory
        """
        self.assert_exists(os.path.join(self.import_dir, *segments))

    def assert_not_in_import_dir(self, *segments):
        """
        Join the ``segments`` and assert that this path does not exist in
        the library directory
        """
        self.assert_does_not_exist(os.path.join(self.import_dir, *segments))

    def assert_islink(self, *segments):
        """
        Join the ``segments`` with the `lib_dir` and assert that this path is a link
        """
        self.assertTrue(os.path.islink(os.path.join(self.lib_dir, *segments)))

    def assert_equal_path(self, path_a, path_b):
        """Check that two paths are equal."""
        self.assertEqual(
            util.normpath(path_a),
            util.normpath(path_b),
            f"paths are not equal: {path_a!r} and {path_b!r}",
        )

    def assert_number_of_files_in_dir(self, count, *segments):
        """
        Assert that there are ``count`` files in path formed by joining ``segments``
        """
        self.assertEqual(len(list(os.listdir(os.path.join(*segments)))), count)


class TestImportSession(importer.ImportSession):
    # pylint: disable=abstract-method
    """ImportSession that can be controlled programaticaly.

    >>> lib = Library(':memory:')
    >>> importer = TestImportSession(lib, paths=['/path/to/import'])
    >>> importer.add_choice(importer.action.SKIP)
    >>> importer.add_choice(importer.action.ASIS)
    >>> importer.default_choice = importer.action.APPLY
    >>> importer.run()

    This imports ``/path/to/import`` into `lib`. It skips the first
    album and imports thesecond one with metadata from the tags. For the
    remaining albums, the metadata from the autotagger will be applied.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._choices = []
        self._resolutions = []

    default_choice = importer.action.APPLY

    def add_choice(self, choice):
        self._choices.append(choice)

    def clear_choices(self):
        self._choices = []

    def choose_match(self, task):
        try:
            choice = self._choices.pop(0)
        except IndexError:
            choice = self.default_choice

        result = choice

        if choice == importer.action.APPLY:
            result = task.candidates[0]

        if isinstance(choice, int):
            result = task.candidates[choice - 1]

        return result

    choose_item = choose_match

    Resolution = Enum("Resolution", "REMOVE SKIP KEEPBOTH")

    default_resolution = "REMOVE"

    def add_resolution(self, resolution):
        # pylint: disable=isinstance-second-argument-not-valid-type
        assert isinstance(resolution, self.Resolution)
        self._resolutions.append(resolution)

    def resolve_duplicate(self, task, found_duplicates):
        try:
            res = self._resolutions.pop(0)
        except IndexError:
            res = self.default_resolution

        if res == self.Resolution.SKIP:
            task.set_choice(importer.action.SKIP)
        elif res == self.Resolution.REMOVE:
            task.should_remove_duplicates = True
