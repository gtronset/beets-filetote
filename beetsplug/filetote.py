"""beets-filetote plugin for beets."""
import filecmp
import os
from dataclasses import asdict, dataclass
from re import match as re_match
from re import sub as re_sub
from typing import Any, List, Optional, Union

from beets import config, util
from beets.library import DefaultTemplateFunctions, Item
from beets.plugins import BeetsPlugin
from beets.ui import get_path_formats
from beets.util import MoveOperation
from beets.util.functemplate import Template
from mediafile import TYPES as BEETS_FILE_TYPES


@dataclass
class FiletoteMapping:
    """Path and nameing Mapping for FileTote Items."""

    artist: str
    albumartist: str
    album: str
    albumpath: str
    medianame_old: str
    medianame_new: str
    old_filename: Optional[str] = None


@dataclass
class FiletoteItem:
    """An individual FileTote Item for processing."""

    path: str
    paired: bool


@dataclass
class FiletoteItemCollection:
    """An individual FileTote Item collection for processing."""

    files: List[FiletoteItem]
    mapping: FiletoteMapping
    source_path: str


@dataclass
class FiletoteSessionData:
    """Configuration settings for FileTote Item."""

    operation: Optional[MoveOperation] = None
    beets_lib = None
    import_path: Optional[bytes] = None


@dataclass
class FiletoteConfig:
    """Configuration settings for FileTote Item."""

    session: FiletoteSessionData = FiletoteSessionData()
    extensions: Union[str, list] = ".*"
    filenames: Union[str, list] = ""
    exclude: Union[str, list] = ""
    print_ignored: bool = False
    pairing: bool = False
    pairing_only: bool = False


class FiletotePlugin(BeetsPlugin):
    """Plugin main class. Eventually, should encompass additional features as
    described in https://github.com/beetbox/beets/wiki/Attachments."""

    # pylint: disable=fixme
    def __init__(self) -> None:
        super().__init__()

        # Set default plugin config settings
        self.config.add(asdict(FiletoteConfig()))

        self.filetote: FiletoteConfig = FiletoteConfig(
            extensions=self.config["extensions"].as_str_seq(),
            filenames=self.config["filenames"].as_str_seq(),
            exclude=self.config["exclude"].as_str_seq(),
            print_ignored=self.config["print_ignored"].get(),
            pairing=self.config["pairing"].get(),
            pairing_only=self.config["pairing_only"].get(),
        )

        queries: List[str] = ["ext:", "filename:", "paired_ext:"]

        self._path_formats: List[tuple] = self._get_filetote_path_formats(
            queries
        )
        self._process_queue: List[FiletoteItemCollection] = []
        self._shared_artifacts: dict = {}
        self._dirs_seen: List[str] = []

        move_events: List[str] = [
            "item_moved",
            "item_copied",
            "item_linked",
            "item_hardlinked",
            "item_reflinked",
        ]

        for move_event in move_events:
            self.register_listener(move_event, self.collect_artifacts)

        self.register_listener("import_begin", self._register_session_settings)
        self.register_listener("cli_exit", self.process_events)

    def _get_filetote_path_formats(self, queries: List[str]) -> List[tuple]:
        path_formats = []

        for path_format in get_path_formats():
            for query in queries:
                if path_format[0].startswith(query):
                    path_formats.append(path_format)
        return path_formats

    def _register_session_settings(self, session):  # type: ignore[no-untyped-def]
        """
        Certain settings are only available and/or finalized once the
        Beets import session begins.

        This also augments the file type list of what is considered a music
        file or media, since MediaFile.TYPES isn't fundamentally a complete
        list of files by extension.
        """

        BEETS_FILE_TYPES.update(
            {
                "m4a": "M4A",
                "wma": "WMA",
                "wave": "WAVE",
            }
        )

        if "audible" in config["plugins"].get():
            BEETS_FILE_TYPES.update({"m4b": "M4B"})

        setattr(self.filetote.session, "operation", self._operation_type())
        self.filetote.session.import_path = os.path.expanduser(session.paths[0])

    def _operation_type(self) -> MoveOperation:
        """Returns the file manipulations type."""

        if config["import"]["move"]:
            operation = MoveOperation.MOVE
        elif config["import"]["copy"]:
            operation = MoveOperation.COPY
        elif config["import"]["link"]:
            operation = MoveOperation.LINK
        elif config["import"]["hardlink"]:
            operation = MoveOperation.HARDLINK
        elif config["import"]["reflink"]:
            operation = MoveOperation.REFLINK
        else:
            operation = None

        return operation

    def _destination(
        self,
        filename: str,
        mapping: FiletoteMapping,
        paired: bool = False,
    ) -> str:
        # pylint: disable=too-many-locals
        """Returns a destination path a file should be moved to. The filename
        is unique to ensure files aren't overwritten. This also checks the
        config for path formats based on file extension allowing the use of
        beets' template functions. If no path formats are found for the file
        extension the original filename is used with the album path.
            - ripped from beets/library.py
        """

        file_name_no_ext = util.displayable_path(os.path.splitext(filename)[0])
        setattr(mapping, "old_filename", file_name_no_ext)

        full_filename = util.displayable_path(filename)
        file_ext = util.displayable_path(os.path.splitext(filename)[1])

        selected_path_query: Optional[str] = None
        selected_path_format: Optional[str] = None

        for query, path_format in self._path_formats:
            ext_len = len("ext:")
            filename_len = len("filename:")
            paired_ext_len = len("paired_ext:")

            if (
                paired
                and query[:paired_ext_len] == "paired_ext:"
                and file_ext == ("." + query[paired_ext_len:].lstrip("."))
            ):
                # Prioritize `filename:` query selectory over `paired_ext:`
                if selected_path_query != "filename:":
                    selected_path_query = "paired_ext:"
                    selected_path_format = path_format
            elif query[:ext_len] == "ext:" and file_ext == (
                "." + query[ext_len:].lstrip(".")
            ):
                # Prioritize `filename:` and `paired_ext:` query selectory over
                # `ext:`
                if selected_path_query not in ["filename:", "paired_ext:"]:
                    selected_path_query = "ext:"
                    selected_path_format = path_format

            elif (
                query[:filename_len] == "filename:"
                and full_filename == query[filename_len:]
            ):
                selected_path_query = "filename:"
                selected_path_format = path_format

        if not selected_path_query:
            # No query matched; use original filename
            file_path = os.path.join(
                mapping.albumpath, util.displayable_path(filename)
            )
            return file_path

        if isinstance(selected_path_format, Template):
            subpath_tmpl = selected_path_format
        else:
            subpath_tmpl = Template(selected_path_format)

        # Get template funcs and evaluate against mapping
        funcs = DefaultTemplateFunctions().functions()
        mapping_dict = asdict(mapping)
        file_path = subpath_tmpl.substitute(mapping_dict, funcs) + file_ext

        # Sanitize filename
        filename = util.sanitize_path(os.path.basename(file_path))
        dirname = os.path.dirname(file_path)
        file_path = os.path.join(dirname, util.displayable_path(filename))

        return file_path

    def _get_formatted(self, value: Any, for_path: bool = False):
        """Replace path separators in value
        - ripped from beets/dbcore/db.py
        """

        if isinstance(value, bytes):
            value = value.decode("utf-8", "ignore")

        if for_path:
            sep_repl = config["path_sep_replace"].as_str()
            sep_drive = config["drive_sep_replace"].as_str()

            if re_match(r"^\w:", value):
                value = re_sub(r"(?<=^\w):", sep_drive, value)

            for sep in (os.path.sep, os.path.altsep):
                if sep:
                    value = value.replace(sep, sep_repl)

        return value

    def _generate_mapping(
        self, beets_item: Item, destination: bytes
    ) -> FiletoteMapping:
        """Creates a mapping of usable path values for renaming. Takes in an
        Item (see https://github.com/beetbox/beets/blob/master/beets/library.py#L456).
        """
        mapping = {
            "artist": beets_item.artist or "None",
            "albumartist": beets_item.albumartist or "None",
            "album": beets_item.album or "None",
        }

        for key in mapping:
            mapping[key] = self._get_formatted(mapping[key])

        album_path = os.path.dirname(destination)
        mapping["albumpath"] = util.displayable_path(album_path)

        # TODO: Retool to utilize the OS's path separator
        # pathsep = config["path_sep_replace"].get(str)
        strpath_old = util.displayable_path(beets_item.path)
        medianame_old, _mediaext_old = os.path.splitext(
            os.path.basename(strpath_old)
        )

        strpath_new = util.displayable_path(destination)
        medianame_new, _mediaext_new = os.path.splitext(
            os.path.basename(strpath_new)
        )

        mapping["medianame_old"] = medianame_old
        mapping["medianame_new"] = medianame_new

        # return mapping
        return FiletoteMapping(
            artist=mapping["artist"],
            albumartist=mapping["albumartist"],
            album=mapping["album"],
            albumpath=mapping["albumpath"],
            medianame_old=mapping["medianame_old"],
            medianame_new=mapping["medianame_new"],
        )

    def _paired_files_collected(
        self, beets_item: Item, source: str, destination: bytes
    ) -> bool:
        item_source_filename, _ext = os.path.splitext(os.path.basename(source))
        source_path: str = os.path.dirname(source)

        queue_files: list[FiletoteItem] = []

        # Check if this path has already been processed
        if source_path in self._dirs_seen:
            # Check to see if "pairing" is enabled and, if so, if there are
            # artifacts to look at
            if self.filetote.pairing and self._shared_artifacts[source_path]:
                # Iterate through shared artifacts to find paired matches
                for filepath in self._shared_artifacts[source_path]:
                    file_name, _file_ext = os.path.splitext(
                        os.path.basename(filepath)
                    )
                    # If the names match, it's a "pair"
                    if file_name == item_source_filename:
                        queue_files.append(
                            FiletoteItem(path=filepath, paired=True)
                        )

                        # Remove from shared artifacts, as the item-move will
                        # handle this file.
                        self._shared_artifacts[source_path].remove(filepath)

                if queue_files:
                    self._process_queue.append(
                        FiletoteItemCollection(
                            files=queue_files,
                            mapping=self._generate_mapping(
                                beets_item, destination
                            ),
                            source_path=source_path,
                        )
                    )
            return True

        return False

    def _is_beets_file_type(self, file_ext: str) -> bool:
        """Checks if the provided file extension is a music file/track
        (i.e., already handles by Beets)."""
        return (
            len(file_ext) > 1
            and util.displayable_path(file_ext)[1:] in BEETS_FILE_TYPES
        )

    def collect_artifacts(
        self, item: Item, source: str, destination: bytes
    ) -> None:
        """Creates lists of the various extra files and artificats for processing.
        """
        item_source_filename = os.path.splitext(os.path.basename(source))[0]
        source_path = os.path.dirname(source)

        queue_files: list[FiletoteItem] = []

        if self._paired_files_collected(item, source, destination):
            return

        non_handled_files = []
        for root, _dirs, files in util.sorted_walk(
            source_path, ignore=config["ignore"].as_str_seq()
        ):
            for filename in files:
                source_file = os.path.join(root, filename)
                file_name, file_ext = os.path.splitext(filename)

                # Skip any files extensions handled by beets
                if self._is_beets_file_type(file_ext):
                    continue

                if not self.filetote.pairing:
                    queue_files.append(
                        FiletoteItem(path=source_file, paired=False)
                    )
                elif (
                    self.filetote.pairing and file_name == item_source_filename
                ):
                    queue_files.append(
                        FiletoteItem(path=source_file, paired=True)
                    )
                else:
                    non_handled_files.append(source_file)

        self._process_queue.append(
            FiletoteItemCollection(
                files=queue_files,
                mapping=self._generate_mapping(item, destination),
                source_path=source_path,
            )
        )
        self._dirs_seen.append(source_path)

        self._shared_artifacts[source_path] = non_handled_files

    def process_events(self, lib):
        """
        Triggered by the CLI exit event, which itself triggers the processing and
        manipuation of the extra files and artificats.
        """
        # Ensure destination library settings are accessible
        setattr(self.filetote.session, "beets_lib", lib)

        for artifact_collection in self._process_queue:
            artifact_collection: FiletoteItemCollection

            artifacts: List[FiletoteItem] = artifact_collection.files

            source_path = artifact_collection.source_path

            if not self.filetote.pairing_only:
                for shared_artifact in self._shared_artifacts[source_path]:
                    artifacts.append(
                        FiletoteItem(path=shared_artifact, paired=False)
                    )

            self._shared_artifacts[source_path] = []

            self.process_artifacts(artifacts, artifact_collection.mapping)

    def process_artifacts(
        self,
        source_artifacts: List[FiletoteItem],
        mapping: FiletoteMapping,
    ):
        """
        Processes and prepares extra files / artifacts for subsequent manipulation.
        """
        if not source_artifacts:
            return

        ignored_files = []

        for artifact in source_artifacts:
            source_file = artifact.path

            source_path = os.path.dirname(source_file)
            # os.path.basename() not suitable here as files may be contained
            # within dir of source_path
            filename = source_file[len(source_path) + 1 :]

            dest_file = self._destination(filename, mapping, artifact.paired)

            # Skip as another plugin or beets has already moved this file
            if not os.path.exists(source_file):
                ignored_files.append(source_file)
                continue

            # Skip if filename is explicitly in `exclude`
            if util.displayable_path(filename) in self.filetote.exclude:
                ignored_files.append(source_file)
                continue

            # Skip:
            # - extensions not allowed in `extensions`
            # - filenames not explicitly in `filenames`
            file_ext = os.path.splitext(filename)[1]
            if (
                ".*" not in self.filetote.extensions
                and util.displayable_path(file_ext)
                not in self.filetote.extensions
                and util.displayable_path(filename)
                not in self.filetote.filenames
            ):
                ignored_files.append(source_file)
                continue

            # Skip file if it already exists in dest
            if os.path.exists(dest_file) and filecmp.cmp(
                source_file, dest_file
            ):
                ignored_files.append(source_file)
                continue

            dest_file = util.unique_path(dest_file)
            util.mkdirall(dest_file)
            dest_file = util.bytestring_path(dest_file)

            self.manipulate_artifact(source_file, dest_file)

        self.print_ignored_files(ignored_files)

    def print_ignored_files(self, ignored_files: list):
        """If enabled in config, output ignored files to beets logs."""

        if self.filetote.print_ignored and ignored_files:
            self._log.warning("Ignored files:")
            for filename in ignored_files:
                self._log.warning("   {0}", os.path.basename(filename))

    def manipulate_artifact(self, source_file, dest_file):
        """Copy, move, link, hardlink or reflink (depending on `operation`)
        the files as well as write metadata.
        NOTE: `operation` should be an instance of `MoveOperation`.
        """

        if not os.path.exists(source_file):
            # Sanity check for other plugins moving files
            return

        # In copy and link modes, treat reimports specially: move in-library
        # files. (Out-of-library files are copied/moved as usual).
        reimport = False

        source_path = os.path.dirname(source_file)

        library_dir = self.filetote.session.beets_lib.directory

        root_path = None

        import_path = self.filetote.session.import_path

        if import_path == library_dir:
            root_path = os.path.dirname(import_path)
            reimport = True
        elif library_dir in util.ancestry(import_path):
            root_path = import_path
            reimport = True

        operation = self.filetote.session.operation

        if reimport:
            operation = "REIMPORT"

        self._log.info(
            f"{operation}-ing artifact:"
            f" {os.path.basename(util.displayable_path(dest_file))}"
        )

        if reimport or operation == MoveOperation.MOVE:
            util.move(source_file, dest_file)

            util.prune_dirs(
                source_path,
                root=root_path,
                clutter=config["clutter"].as_str_seq(),
            )
        elif operation == MoveOperation.COPY:
            util.copy(source_file, dest_file)
        elif operation == MoveOperation.LINK:
            util.link(source_file, dest_file)
        elif operation == MoveOperation.HARDLINK:
            util.hardlink(source_file, dest_file)
        elif operation == MoveOperation.REFLINK:
            util.reflink(source_file, dest_file, fallback=False)
        elif operation == MoveOperation.REFLINK_AUTO:
            util.reflink(source_file, dest_file, fallback=True)
        else:
            assert False, f"unknown MoveOperation {operation}"
