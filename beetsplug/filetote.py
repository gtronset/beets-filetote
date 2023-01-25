"""beets-filetote plugin for beets."""
import filecmp
import os
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

from beets import config, util
from beets.library import DefaultTemplateFunctions
from beets.plugins import BeetsPlugin
from beets.ui import get_path_formats
from beets.util import MoveOperation
from beets.util.functemplate import Template
from mediafile import TYPES as BEETS_FILE_TYPES

from .filetote_dataclasses import (
    FiletoteArtifact,
    FiletoteArtifactCollection,
    FiletoteConfig,
    FiletotePairingData,
    FiletoteSessionData,
)
from .mapping_model import FiletoteMappingFormatted, FiletoteMappingModel

if TYPE_CHECKING:
    from beets.importer import ImportSession
    from beets.library import Item, Library


class FiletotePlugin(BeetsPlugin):
    """Plugin main class. Eventually, should encompass additional features as
    described in https://github.com/beetbox/beets/wiki/Attachments."""

    def __init__(self) -> None:
        super().__init__()

        # Set default plugin config settings
        self.config.add(FiletoteConfig().asdict())

        self.filetote: FiletoteConfig = FiletoteConfig(
            session=FiletoteSessionData(),
            extensions=self.config["extensions"].as_str_seq(),
            filenames=self.config["filenames"].as_str_seq(),
            exclude=self.config["exclude"].as_str_seq(),
            print_ignored=self.config["print_ignored"].get(),
            pairing=FiletotePairingData(**self.config["pairing"].get(dict)),
        )

        queries: List[str] = ["ext:", "filename:", "paired_ext:"]

        self._path_formats: List[tuple] = self._get_filetote_path_formats(queries)
        self._process_queue: List[FiletoteArtifactCollection] = []
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
        """Gets all `path` formats from beets and parses those set for Filetote."""
        path_formats = []

        for path_format in get_path_formats():
            for query in queries:
                if path_format[0].startswith(query):
                    path_formats.append(path_format)
        return path_formats

    def _register_session_settings(self, session: "ImportSession"):
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

        self.filetote.session.adjust("operation", self._operation_type())
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

    def _get_path_query_format_match(
        self, artifact_filename: str, artifact_ext: str, paired: bool
    ) -> tuple:
        full_filename = util.displayable_path(artifact_filename)

        selected_path_query: Optional[str] = None
        selected_path_format: Optional[str] = None

        for query, path_format in self._path_formats:
            ext_len: int = len("ext:")
            filename_len: int = len("filename:")
            paired_ext_len: int = len("paired_ext:")

            if (
                paired
                and query[:paired_ext_len] == "paired_ext:"
                and artifact_ext == ("." + query[paired_ext_len:].lstrip("."))
            ):
                # Prioritize `filename:` query selectory over `paired_ext:`
                if selected_path_query != "filename:":
                    selected_path_query = "paired_ext:"
                    selected_path_format = path_format
            elif query[:ext_len] == "ext:" and artifact_ext == (
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

        return (selected_path_query, selected_path_format)

    def _get_artifact_destination(
        self,
        artifact_filename: str,
        mapping: FiletoteMappingModel,
        paired: bool = False,
    ) -> str:
        """
        Returns a destination path aan artifact/file should be moved to. The
        artifact filename is unique to ensure files aren't overwritten. This also
        checks the config for path formats based on file extension allowing the use of
        beets' template functions. If no path formats are found for the file extension
        the original filename is used with the album path.
        """

        artifact_filename_no_ext = util.displayable_path(
            os.path.splitext(artifact_filename)[0]
        )
        mapping.set("old_filename", artifact_filename_no_ext)

        mapping_formatted = FiletoteMappingFormatted(
            mapping, for_path=True, whitelist_replace=["albumpath"]
        )

        artifact_ext = util.displayable_path(os.path.splitext(artifact_filename)[1])

        (
            selected_path_query,
            selected_path_format,
        ) = self._get_path_query_format_match(artifact_filename, artifact_ext, paired)

        if not selected_path_query:
            # No query matched; use original filename
            artifact_path = os.path.join(
                mapping_formatted.get("albumpath"),
                util.displayable_path(artifact_filename),
            )
            return artifact_path

        subpath_tmpl = self._templatize_path_format(selected_path_format)

        # Get template funcs and evaluate against mapping
        template_functions = DefaultTemplateFunctions().functions()
        artifact_path = (
            subpath_tmpl.substitute(mapping_formatted, template_functions)
            + artifact_ext
        )

        # Sanitize filename
        artifact_filename = util.sanitize_path(os.path.basename(artifact_path))
        dirname = os.path.dirname(artifact_path)
        artifact_path = os.path.join(dirname, util.displayable_path(artifact_filename))

        return artifact_path

    def _templatize_path_format(self, path_format: Union[str, Template]) -> Template:
        """Ensures that the path format is a Beets Template."""
        if isinstance(path_format, Template):
            subpath_tmpl = path_format
        else:
            subpath_tmpl = Template(path_format)

        return subpath_tmpl

    def _generate_mapping(
        self, beets_item: "Item", destination: bytes
    ) -> FiletoteMappingModel:
        """Creates a mapping of usable path values for renaming. Takes in an
        Item (see https://github.com/beetbox/beets/blob/master/beets/library.py#L456).
        """

        album_path = os.path.dirname(destination)

        strpath_old = util.displayable_path(beets_item.path)
        medianame_old, _ = os.path.splitext(os.path.basename(strpath_old))

        strpath_new = util.displayable_path(destination)
        medianame_new, _ = os.path.splitext(os.path.basename(strpath_new))

        mapping_meta = {
            "artist": beets_item.artist or "None",
            "albumartist": beets_item.albumartist or "None",
            "album": beets_item.album or "None",
            "albumpath": util.displayable_path(album_path),
            "medianame_old": medianame_old,
            "medianame_new": medianame_new,
        }

        return FiletoteMappingModel(**mapping_meta)

    def _collect_paired_artifacts(
        self, beets_item: "Item", source: str, destination: bytes
    ) -> None:
        """
        When file "pairing" is enabled, this function looks through available
        artifacts for potential matching pairs. When found, it processes the artifacts
        to be handled specifically as a "pair".
        """

        item_source_filename, _ext = os.path.splitext(os.path.basename(source))
        source_path: str = os.path.dirname(source)

        queue_artifacts: list[FiletoteArtifact] = []

        # Check to see if "pairing" is enabled and, if so, if there are
        # artifacts to look at
        if self.filetote.pairing.enabled and self._shared_artifacts[source_path]:
            # Iterate through shared artifacts to find paired matches
            for artifact_path in self._shared_artifacts[source_path]:
                artifact_filename, artifact_ext = os.path.splitext(
                    os.path.basename(artifact_path)
                )
                # If the names match and it's an authorized extension, it's a "pair"
                if artifact_filename == item_source_filename and (
                    ".*" in self.filetote.pairing.extensions
                    or artifact_ext in self.filetote.pairing.extensions
                ):
                    queue_artifacts.append(
                        FiletoteArtifact(path=artifact_path, paired=True)
                    )

                    # Remove from shared artifacts, as the item-move will
                    # handle this file.
                    self._shared_artifacts[source_path].remove(artifact_path)

            if queue_artifacts:
                self._process_queue.append(
                    FiletoteArtifactCollection(
                        artifacts=queue_artifacts,
                        mapping=self._generate_mapping(beets_item, destination),
                        source_path=source_path,
                    )
                )

    def _is_beets_file_type(self, file_ext: str) -> bool:
        """Checks if the provided file extension is a music file/track
        (i.e., already handles by Beets)."""
        return (
            len(file_ext) > 1
            and util.displayable_path(file_ext)[1:] in BEETS_FILE_TYPES
        )

    def collect_artifacts(self, item: "Item", source: str, destination: bytes) -> None:
        """
        Creates lists of the various extra files and artificats for processing.
        Since beets passes through the arguments, it's explicitly setting the Item to
        the `item` argument (as it does with the others).
        """
        item_source_filename = os.path.splitext(os.path.basename(source))[0]
        source_path = os.path.dirname(source)

        queue_files: list[FiletoteArtifact] = []

        # Check if this path has not already been processed
        if source_path in self._dirs_seen:
            self._collect_paired_artifacts(item, source, destination)
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

                if not self.filetote.pairing.enabled:
                    queue_files.append(FiletoteArtifact(path=source_file, paired=False))
                elif (
                    self.filetote.pairing.enabled
                    and file_name == item_source_filename
                    and (
                        ".*" in self.filetote.pairing.extensions
                        or file_ext.decode("utf-8") in self.filetote.pairing.extensions
                    )
                ):
                    queue_files.append(FiletoteArtifact(path=source_file, paired=True))
                else:
                    non_handled_files.append(source_file)

        self._process_queue.append(
            FiletoteArtifactCollection(
                artifacts=queue_files,
                mapping=self._generate_mapping(item, destination),
                source_path=source_path,
            )
        )
        self._dirs_seen.append(source_path)

        self._shared_artifacts[source_path] = non_handled_files

    def process_events(self, lib: "Library") -> None:
        """
        Triggered by the CLI exit event, which itself triggers the processing and
        manipuation of the extra files and artificats.
        """
        # Ensure destination library settings are accessible
        self.filetote.session.adjust("beets_lib", lib)

        artifact_collection: FiletoteArtifactCollection
        for artifact_collection in self._process_queue:
            artifacts: List[FiletoteArtifact] = artifact_collection.artifacts

            source_path = artifact_collection.source_path

            if not self.filetote.pairing.pairing_only:
                for shared_artifact in self._shared_artifacts[source_path]:
                    artifacts.append(
                        FiletoteArtifact(path=shared_artifact, paired=False)
                    )

            self._shared_artifacts[source_path] = []

            self.process_artifacts(artifacts, artifact_collection.mapping)

    def _is_artifact_ignorable(
        self, artifact_source: str, artifact_filename: str, artifact_dest: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Compares the artifact/file to certain checks to see if it should be ignored
        or skipped.
        """

        # Skip/ignore as another plugin or beets has already moved this file
        if not os.path.exists(artifact_source):
            return (True, artifact_source)

        # Skip if filename is explicitly in `exclude`
        if util.displayable_path(artifact_filename) in self.filetote.exclude:
            return (True, artifact_source)

        # Skip:
        # - extensions not allowed in `extensions`
        # - filenames not explicitly in `filenames`
        artifact_file_ext = os.path.splitext(artifact_filename)[1]
        if (
            ".*" not in self.filetote.extensions
            and util.displayable_path(artifact_file_ext) not in self.filetote.extensions
            and util.displayable_path(artifact_filename) not in self.filetote.filenames
        ):
            return (True, artifact_source)

        # Skip file if it already exists in dest
        if os.path.exists(artifact_dest) and filecmp.cmp(
            artifact_source, artifact_dest
        ):
            return (True, artifact_source)

        return (False, None)

    def process_artifacts(
        self,
        source_artifacts: List[FiletoteArtifact],
        mapping: FiletoteMappingModel,
    ) -> None:
        """
        Processes and prepares extra files / artifacts for subsequent manipulation.
        """
        if not source_artifacts:
            return

        ignored_artifacts: List = []

        for artifact in source_artifacts:
            artifact_source = artifact.path

            source_path = os.path.dirname(artifact_source)
            # os.path.basename() not suitable here as files may be contained
            # within dir of source_path
            artifact_filename = artifact_source[len(source_path) + 1 :]

            artifact_dest = self._get_artifact_destination(
                artifact_filename, mapping, artifact.paired
            )

            is_ignorable, ignore_filename = self._is_artifact_ignorable(
                artifact_source=artifact_source,
                artifact_filename=artifact_filename,
                artifact_dest=artifact_dest,
            )

            if is_ignorable:
                ignored_artifacts.append(ignore_filename)
                continue

            artifact_dest = util.unique_path(artifact_dest)
            util.mkdirall(artifact_dest)
            artifact_dest = util.bytestring_path(artifact_dest)

            self.manipulate_artifact(artifact_source, artifact_dest)

        self.print_ignored_artifacts(ignored_artifacts)

    def print_ignored_artifacts(self, ignored_artifacts: list) -> None:
        """If enabled in config, output ignored files to beets logs."""

        if self.filetote.print_ignored and ignored_artifacts:
            self._log.warning("Ignored files:")
            for artifact_filename in ignored_artifacts:
                self._log.warning("   {0}", os.path.basename(artifact_filename))

    def manipulate_artifact(self, artifact_source: str, artifact_dest: str) -> None:
        """
        Copy, move, link, hardlink or reflink (depending on `operation`)
        the artifacts (as well as write metadata).
        NOTE: `operation` should be an instance of `MoveOperation`.
        """
        # pylint: disable=too-many-branches

        if not os.path.exists(artifact_source):
            # Sanity check for other plugins moving files
            return

        # In copy and link modes, treat reimports specially: move in-library
        # files. (Out-of-library files are copied/moved as usual).
        reimport = False

        source_path = os.path.dirname(artifact_source)

        # Sanity check for pylint in cases where beets_lib is None
        if not self.filetote.session.beets_lib:
            return

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
            f" {os.path.basename(util.displayable_path(artifact_dest))}"
        )

        if operation in [MoveOperation.MOVE, "REIMPORT"]:
            util.move(artifact_source, artifact_dest)

            util.prune_dirs(
                source_path,
                root=root_path,
                clutter=config["clutter"].as_str_seq(),
            )
        elif operation == MoveOperation.COPY:
            util.copy(artifact_source, artifact_dest)
        elif operation == MoveOperation.LINK:
            util.link(artifact_source, artifact_dest)
        elif operation == MoveOperation.HARDLINK:
            util.hardlink(artifact_source, artifact_dest)
        elif operation == MoveOperation.REFLINK:
            util.reflink(artifact_source, artifact_dest, fallback=False)
        elif operation == MoveOperation.REFLINK_AUTO:
            util.reflink(artifact_source, artifact_dest, fallback=True)
        else:
            assert False, f"unknown MoveOperation {operation}"
