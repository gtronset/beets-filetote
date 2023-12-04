"""beets-filetote plugin for beets."""

import filecmp
import fnmatch
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union

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

        config_paths: Dict[str, Any] = self.config["paths"].get(dict)

        self.filetote: FiletoteConfig = FiletoteConfig(
            extensions=self.config["extensions"].as_str_seq(),
            filenames=self.config["filenames"].as_str_seq(),
            patterns=self.config["patterns"].get(dict),
            paths=self._templatize_config_paths(config_paths),
            exclude=self.config["exclude"].as_str_seq(),
            print_ignored=self.config["print_ignored"].get(bool),
        )

        self.filetote.adjust(
            "pairing",
            {
                "enabled": self.config["pairing"]["enabled"].get(bool),
                "pairing_only": self.config["pairing"]["pairing_only"].get(bool),
                "extensions": self.config["pairing"]["extensions"].as_str_seq(),
            },
        )

        queries: List[str] = ["ext:", "filename:", "paired_ext:", "pattern:"]

        self._path_formats: Dict[str, Template] = self._get_filetote_path_formats(
            queries
        )
        self._process_queue: List[FiletoteArtifactCollection] = []
        self._shared_artifacts: Dict[bytes, List[bytes]] = {}
        self._dirs_seen: List[bytes] = []

        self._register_file_operation_events()

    def _register_file_operation_events(self) -> None:
        """
        Registers various file operation events and their corresponding functions.

        This method creates functions for file operation events like moving, copying,
        linking, etc., and registers them as listeners for corresponding Beets events.
        It also registers other necessary listeners for plugin functionality
        (`pluginload`, `import_begin`, and `cli_exit`) which do not utilize generated
        function wrappers.

        These functions act as wrappers for Beets events, forwarding the event name
        to the target function (e.g., 'move_event_listener()') along with any additional
        event-specific arguments.

        Note: The `file_operation_event_functions` dictionary stores the event name and
        its corresponding generated function.
        """
        file_operation_events: List[str] = [
            "before_item_moved",
            "item_copied",
            "item_linked",
            "item_hardlinked",
            "item_reflinked",
        ]

        file_operation_event_functions: Dict[str, Callable[..., None]] = {}

        for event in file_operation_events:
            file_operation_event_functions[event] = self._build_file_event_function(
                event
            )

            self.register_listener(event, file_operation_event_functions[event])

        self.register_listener("pluginload", self._register_additional_file_types)

        self.register_listener("import_begin", self._register_session_settings)

        self.register_listener("cli_exit", self.process_events)

    def _build_file_event_function(self, event: str) -> Callable[..., None]:
        """
        Creates a function that acts as a wrapper for specific file operation events
        triggered by Beets, forwarding the event name to the corresponding target
        function.
        """

        def file_event_function(**kwargs: Any) -> None:
            self.file_operation_event_listener(event, **kwargs)

        return file_event_function

    def _get_filetote_path_formats(self, queries: List[str]) -> Dict[str, Template]:
        """
        Gets all `path` formats from beets and parses those set for Filetote.
        First sets those from the Beet's `path` node then sets them from
        Filetote's node, overriding when needed to give priority to Filetote's
        definitions.
        """
        path_formats: Dict[str, Template] = {}

        for beets_path_format in get_path_formats():
            for query in queries:
                if beets_path_format[0].startswith(query):
                    path_formats[beets_path_format[0]] = beets_path_format[1]

        path_formats.update(self.filetote.paths)

        return path_formats

    def _register_additional_file_types(self) -> None:
        """
        This augments the file type list of what is considered a music
        file or media, since MediaFile.TYPES isn't fundamentally a complete
        list of files by extension.
        """
        BEETS_FILE_TYPES.update({
            "m4a": "M4A",
            "wma": "WMA",
            "wave": "WAVE",
        })

        if "audible" in config["plugins"].get():
            BEETS_FILE_TYPES.update({"m4b": "M4B"})

    def _register_session_settings(self, session: "ImportSession") -> None:
        """
        Certain settings are only available and/or finalized once the
        Beets import session begins.
        """

        self.filetote.session.adjust("operation", self._import_operation_type())

        import_path: Optional[bytes] = None

        if session.paths:
            import_path = os.path.expanduser(session.paths[0])

        self.filetote.session.import_path = import_path

    def _import_operation_type(self) -> Union[MoveOperation, None]:
        """
        Returns the file manipulations type. This prioritizes `move` over copy if
        present.
        """

        mapping = {
            "move": MoveOperation.MOVE,
            "copy": MoveOperation.COPY,
            "link": MoveOperation.LINK,
            "hardlink": MoveOperation.HARDLINK,
            "reflink": MoveOperation.REFLINK,
        }

        for operation_type, operation in mapping.items():
            if config["import"][operation_type]:
                return operation

        return None

    def _event_operation_type(self, event: str) -> Union[MoveOperation, None]:
        """Returns the file manipulations type. Requires a Beets event to be provided
        and the operation type is inferred based on the event name/type.
        """

        mapping = {
            "before_item_moved": MoveOperation.MOVE,
            "item_copied": MoveOperation.COPY,
            "item_linked": MoveOperation.LINK,
            "item_hardlinked": MoveOperation.HARDLINK,
            "item_reflinked": MoveOperation.REFLINK,
        }

        return mapping.get(event, None)

    def file_operation_event_listener(
        self, event: str, item: "Item", source: bytes, destination: bytes
    ) -> None:
        """
        Certain CLI opertations such as `move` (`mv`) don't utilize the config file's
        `import` settings which `_operation_type()` uses by default to determine how
        Filetote should move/copy the file. Since there are not otherwise any indicators
        of this, the operation type is inferred based on the event name/type.

        These events should only be emitted in cases where something happens to the
        media files, and this should only have to fall back to infer from event types
        for similar aforementioned CLI commands.
        """
        # Detmine the opteration type if not already present
        if not self.filetote.session.operation:
            self.filetote.session.adjust("operation", self._event_operation_type(event))

        # Find and collect all non-media file artifacts
        self.collect_artifacts(item, source, destination)

    def remove_prefix(self, text: str, prefix: str) -> str:
        """Removes the prefix of given text."""
        if text.startswith(prefix):
            return text[len(prefix) :]
        return text

    def _get_path_query_format_match(
        self,
        artifact_filename: str,
        artifact_ext: str,
        paired: bool,
        pattern_category: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[Template]]:
        """
        Calculate the best path query format, prioritizing:

        1. `filename:`
        2. `paired_ext:`
        3. `pattern:`
        4. `ext:`
        """
        full_filename: str = util.displayable_path(artifact_filename)

        selected_path_query: Optional[str] = None
        selected_path_format: Optional[Template] = None

        for query, path_format in self._path_formats.items():
            filename_prefix: str = "filename:"
            paired_ext_prefix: str = "paired_ext:"
            pattern_prefix: str = "pattern:"
            ext_prefix: str = "ext:"

            if (
                paired
                and query.startswith(paired_ext_prefix)
                and artifact_ext
                == ("." + self.remove_prefix(query, paired_ext_prefix).lstrip("."))
            ):
                # Prioritize `filename:` query selectory over `paired_ext:`
                if selected_path_query != filename_prefix:
                    selected_path_query = paired_ext_prefix
                    selected_path_format = path_format
            elif (
                pattern_category
                and not query.startswith(
                    (filename_prefix, paired_ext_prefix, ext_prefix)
                )
                and self.remove_prefix(query, pattern_prefix) == pattern_category
            ):
                # This should pull the corresponding pattern def,
                # Prioritize `filename:` and `paired_ext:` query selectory over
                # `pattern:`
                if selected_path_query not in [filename_prefix, paired_ext_prefix]:
                    selected_path_query = pattern_prefix
                    selected_path_format = path_format
            elif query.startswith(ext_prefix) and artifact_ext == (
                "." + self.remove_prefix(query, ext_prefix).lstrip(".")
            ):
                # Prioritize `filename:`, `paired_ext:`, and `pattern:` query selector
                #  over `ext:`
                if selected_path_query not in [
                    filename_prefix,
                    paired_ext_prefix,
                    pattern_prefix,
                ]:
                    selected_path_query = ext_prefix
                    selected_path_format = path_format
            elif query.startswith(
                filename_prefix
            ) and full_filename == self.remove_prefix(query, filename_prefix):
                selected_path_query = filename_prefix
                selected_path_format = path_format

        return (selected_path_query, selected_path_format)

    def _get_artifact_destination(
        self,
        artifact_filename: bytes,
        mapping: FiletoteMappingModel,
        paired: bool = False,
        pattern_category: Optional[str] = None,
    ) -> bytes:
        # pylint: disable=too-many-locals
        """
        Returns a destination path an artifact/file should be moved to. The
        artifact filename is unique to ensure files aren't overwritten. This also
        checks the config for path formats based on file extension allowing the use of
        beets' template functions. If no path formats are found for the file extension
        the original filename is used with the album path.
        """

        artifact_filename_no_ext: str = util.displayable_path(
            os.path.splitext(artifact_filename)[0]
        )
        mapping.set("old_filename", artifact_filename_no_ext)

        mapping_formatted = FiletoteMappingFormatted(
            mapping, for_path=True, whitelist_replace=["albumpath"]
        )

        artifact_ext: str = util.displayable_path(
            os.path.splitext(artifact_filename)[1]
        )

        (
            selected_path_query,
            selected_path_format,
        ) = self._get_path_query_format_match(
            util.displayable_path(artifact_filename),
            artifact_ext,
            paired,
            pattern_category,
        )

        album_path: Optional[str] = mapping_formatted.get("albumpath")
        assert album_path is not None

        if not selected_path_query:
            # No query matched; use original filename
            artifact_path: str = os.path.join(
                album_path,
                util.displayable_path(artifact_filename),
            )
            return util.bytestring_path(artifact_path)

        assert selected_path_format is not None
        subpath_tmpl: Template = self._templatize_path_format(selected_path_format)

        # Get template funcs and evaluate against mapping
        template_functions = DefaultTemplateFunctions().functions()
        artifact_path = (
            subpath_tmpl.substitute(mapping_formatted, template_functions)
            + artifact_ext
        )

        # Sanitize filename
        artifact_filename_sanitized: str = util.sanitize_path(
            os.path.basename(artifact_path)
        )
        dirname: str = os.path.dirname(artifact_path)
        artifact_path_sanitized: str = os.path.join(
            dirname, util.displayable_path(artifact_filename_sanitized)
        )

        return util.bytestring_path(artifact_path_sanitized)

    def _templatize_path_format(self, path_format: Union[str, Template]) -> Template:
        """Ensures that the path format is a Beets Template."""
        subpath_tmpl: Template

        if isinstance(path_format, Template):
            subpath_tmpl = path_format
        else:
            subpath_tmpl = Template(path_format)

        return subpath_tmpl

    def _templatize_config_paths(
        self, paths: Dict[str, Union[str, Template]]
    ) -> Dict[str, Template]:
        """Ensures that the path format is a Beets Template."""
        templatized_paths: Dict[str, Template] = {}
        for path_key, path_value in paths.items():
            templatized_paths[path_key] = self._templatize_path_format(path_value)
        return templatized_paths

    def _generate_mapping(
        self, beets_item: "Item", destination: bytes
    ) -> FiletoteMappingModel:
        """Creates a mapping of usable path values for renaming. Takes in an
        Item (see https://github.com/beetbox/beets/blob/master/beets/library.py#L456).
        """

        album_path: bytes = os.path.dirname(destination)

        medianame_old: bytes
        medianame_old, _ = os.path.splitext(os.path.basename(beets_item.path))

        medianame_new: bytes
        medianame_new, _ = os.path.splitext(os.path.basename(destination))

        mapping_meta = {
            "albumpath": util.displayable_path(album_path),
            "medianame_old": util.displayable_path(medianame_old),
            "medianame_new": util.displayable_path(medianame_new),
        }

        # Include all normal Item fields, using the formatted values
        mapping_meta.update(beets_item.formatted())

        return FiletoteMappingModel(**mapping_meta)

    def _collect_paired_artifacts(
        self, beets_item: "Item", source: bytes, destination: bytes
    ) -> None:
        """
        When file "pairing" is enabled, this function looks through available
        artifacts for potential matching pairs. When found, it processes the artifacts
        to be handled specifically as a "pair".
        """

        item_source_filename: bytes
        item_source_filename, _ = os.path.splitext(os.path.basename(source))
        source_path: bytes = os.path.dirname(source)

        queue_artifacts: list[FiletoteArtifact] = []

        # Check to see if "pairing" is enabled and, if so, if there are
        # artifacts to look at
        if self.filetote.pairing.enabled and self._shared_artifacts[source_path]:
            # Iterate through shared artifacts to find paired matches
            for artifact_path in self._shared_artifacts[source_path]:
                artifact_filename: bytes
                artifact_ext: bytes
                artifact_filename, artifact_ext = os.path.splitext(
                    os.path.basename(artifact_path)
                )
                # If the names match and it's an valid extension, it's a "pair"
                if (
                    artifact_filename == item_source_filename
                    and self._is_valid_paired_extension(artifact_ext)
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

    def _is_beets_file_type(self, file_ext: Union[str, bytes]) -> bool:
        """Checks if the provided file extension is a music file/track
        (i.e., already handles by Beets)."""
        return (
            len(file_ext) > 1
            and util.displayable_path(file_ext)[1:] in BEETS_FILE_TYPES
        )

    def collect_artifacts(
        self, item: "Item", source: bytes, destination: bytes
    ) -> None:
        """
        Creates lists of the various extra files and artificats for processing.
        Since beets passes through the arguments, it's explicitly setting the Item to
        the `item` argument (as it does with the others).

        `source` is a `PathType`, which according to the beets docs:
        > are represented as `bytes` objects, in keeping with the Unix filesystem
        > abstraction.
        """
        item_source_filename: bytes = os.path.splitext(os.path.basename(source))[0]
        source_path: bytes = os.path.dirname(source)

        queue_files: list[FiletoteArtifact] = []

        # Check if this path has not already been processed
        if source_path in self._dirs_seen:
            self._collect_paired_artifacts(item, source, destination)
            return

        non_handled_files: List[bytes] = []
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
                    and self._is_valid_paired_extension(file_ext)
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

            source_path: bytes = artifact_collection.source_path

            if not self.filetote.pairing.pairing_only:
                for shared_artifact in self._shared_artifacts[source_path]:
                    artifacts.append(
                        FiletoteArtifact(path=shared_artifact, paired=False)
                    )

            self._shared_artifacts[source_path] = []

            self.process_artifacts(
                source_path=source_path,
                source_artifacts=artifacts,
                mapping=artifact_collection.mapping,
            )

    def _is_valid_paired_extension(self, artifact_file_ext: Union[str, bytes]) -> bool:
        return (
            ".*" in self.filetote.pairing.extensions
            or util.displayable_path(artifact_file_ext)
            in self.filetote.pairing.extensions
        )

    def _is_pattern_match(
        self, artifact_relpath: bytes, match_category: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if the file is in the defined patterns."""

        pattern_definitions: List[Tuple[str, List[str]]] = list(
            self.filetote.patterns.items()
        )

        if match_category:
            pattern_definitions = [
                (match_category, self.filetote.patterns[match_category])
            ]

        for category, patterns in pattern_definitions:
            for pattern in patterns:
                is_match: bool = False

                if pattern.endswith("/"):
                    for path in util.ancestry(artifact_relpath):
                        if not fnmatch.fnmatch(
                            util.displayable_path(path), pattern.strip("/")
                        ):
                            continue
                        is_match = True
                else:
                    is_match = fnmatch.fnmatch(
                        util.displayable_path(artifact_relpath), pattern.lstrip("/")
                    )

                if is_match:
                    return (is_match, category)

        return (False, None)

    def _is_artifact_ignorable(
        self,
        source_path: bytes,
        artifact_source: bytes,
        artifact_filename: bytes,
        artifact_paired: bool,
    ) -> Tuple[bool, Optional[str]]:
        """
        Compares the artifact/file to certain checks to see if it should be ignored
        or skipped.
        """

        # Skip/ignore as another plugin or beets has already moved this file
        if not os.path.exists(artifact_source):
            return (True, None)

        # Skip if filename is explicitly in `exclude`
        if util.displayable_path(artifact_filename) in self.filetote.exclude:
            return (True, None)

        # Skip:
        # - extensions not allowed in `extensions`
        # - filenames not explicitly in `filenames`
        # - non-paired files
        # - artifacts not matching patterns

        artifact_file_ext: str = util.displayable_path(
            os.path.splitext(artifact_filename)[1]
        )

        relpath: bytes = os.path.relpath(artifact_source, start=source_path)

        is_pattern_match: bool
        category: Optional[str]
        is_pattern_match, category = self._is_pattern_match(artifact_relpath=relpath)

        if (
            ".*" not in self.filetote.extensions
            and util.displayable_path(artifact_file_ext) not in self.filetote.extensions
            and util.displayable_path(artifact_filename) not in self.filetote.filenames
            and not is_pattern_match
            and not (
                artifact_paired and self._is_valid_paired_extension(artifact_file_ext)
            )
        ):
            return (True, None)

        matched_category: Optional[str] = None
        if is_pattern_match:
            matched_category = category

        return (False, matched_category)

    def _artifact_exists_in_dest(
        self,
        artifact_source: bytes,
        artifact_dest: bytes,
    ) -> bool:
        """
        Checks if the artifact/file already exists in the destination destination,
        which would also make it ignorable.
        """

        # Skip file
        return os.path.exists(artifact_dest) and filecmp.cmp(
            artifact_source, artifact_dest
        )

    def process_artifacts(
        self,
        source_path: bytes,
        source_artifacts: List[FiletoteArtifact],
        mapping: FiletoteMappingModel,
    ) -> None:
        """
        Processes and prepares extra files and artifacts for subsequent manipulation.
        """
        if not source_artifacts:
            return

        ignored_artifacts: List[bytes] = []

        for artifact in source_artifacts:
            artifact_source: bytes = artifact.path

            artifact_path: bytes = os.path.dirname(artifact_source)

            # os.path.basename() not suitable here as files may be contained
            # within dir of source_path
            artifact_filename: bytes = artifact_source[len(artifact_path) + 1 :]

            is_ignorable: bool
            pattern_category: Optional[str]
            is_ignorable, pattern_category = self._is_artifact_ignorable(
                source_path=source_path,
                artifact_source=artifact_source,
                artifact_filename=artifact_filename,
                artifact_paired=artifact.paired,
            )

            if is_ignorable:
                ignored_artifacts.append(artifact_filename)
                continue

            artifact_dest: bytes = self._get_artifact_destination(
                artifact_filename, mapping, artifact.paired, pattern_category
            )

            if self._artifact_exists_in_dest(
                artifact_source=artifact_source,
                artifact_dest=artifact_dest,
            ):
                ignored_artifacts.append(artifact_filename)
                continue

            artifact_dest = util.unique_path(artifact_dest)
            util.mkdirall(artifact_dest)

            # In copy and link modes, treat reimports specially: move in-library
            # files. (Out-of-library files are copied/moved as usual).
            reimport: bool = self._is_reimport()

            operation: Optional[MoveOperation] = self.filetote.session.operation

            self.manipulate_artifact(
                operation, artifact_source, artifact_dest, reimport
            )

            if operation == MoveOperation.MOVE or reimport:
                # Prune vacated directory. Depending on the type of operation,
                # this might be a specific import path, the base library, etc.
                root_path: Optional[bytes] = self._get_prune_root_path()

                util.prune_dirs(
                    source_path,
                    root=root_path,
                    clutter=config["clutter"].as_str_seq(),
                )

        self.print_ignored_artifacts(ignored_artifacts)

    def print_ignored_artifacts(self, ignored_artifacts: List[bytes]) -> None:
        """If enabled in config, output ignored files to beets logs."""

        if self.filetote.print_ignored and ignored_artifacts:
            self._log.warning("Ignored files:")
            for artifact_filename in ignored_artifacts:
                self._log.warning("   {0}", os.path.basename(artifact_filename))

    def _is_import_path_same_as_library_dir(
        self, import_path: Optional[bytes], library_dir: bytes
    ) -> bool:
        """Checks if the import path matches the library directory."""
        return import_path is not None and import_path == library_dir

    def _is_import_path_within_library(
        self, import_path: Optional[bytes], library_dir: bytes
    ) -> bool:
        """Checks if the import path is within the library directory."""
        return import_path is not None and str(library_dir) in util.ancestry(
            import_path
        )

    def _is_reimport(self) -> bool:
        """
        Checks if the import is considered a "reimport".

        Copy and link modes treat reimports specially, where in-library files
        are moved.
        """

        # Sanity check for pylint in cases where beets_lib is None
        assert self.filetote.session.beets_lib is not None

        library_dir = self.filetote.session.beets_lib.directory
        import_path = self.filetote.session.import_path

        return self._is_import_path_same_as_library_dir(
            import_path, library_dir
        ) or self._is_import_path_within_library(import_path, library_dir)

    def _get_prune_root_path(self) -> Optional[bytes]:
        """
        Deduces the root path for cleaning up dangling files on MOVE.

        This method determines the root path that aids in cleaning up files
        when moving. If the import path matches the library directory or is
        within it, the root path is selected. Otherwise, returns None.
        """

        # Sanity check for pylint in cases where beets_lib is None
        assert self.filetote.session.beets_lib is not None

        library_dir = self.filetote.session.beets_lib.directory
        import_path = self.filetote.session.import_path

        root_path: Optional[bytes] = None

        if import_path is None:
            # If there's not a import path (query, other CLI, etc.), use the
            # Library's dir instead. This is consistent with beet's default
            # pruning for MOVE.
            root_path = library_dir
        elif self._is_import_path_same_as_library_dir(import_path, library_dir):
            # If the import path is the same as the Library's, allow for
            # pruning all the way to the library path.
            root_path = os.path.dirname(import_path)
        elif self._is_import_path_within_library(import_path, library_dir):
            # Otherwise, prune all the way up to the import path.
            root_path = import_path

        return root_path

    def manipulate_artifact(
        self,
        operation: Optional[MoveOperation],
        artifact_source: bytes,
        artifact_dest: bytes,
        reimport: Optional[bool] = False,
    ) -> None:
        """
        Copy, move, link, hardlink or reflink (depending on `operation`)
        the artifacts (as well as write metadata).
        NOTE: `operation` should be an instance of `MoveOperation`.

        If the operation is copy or a link but it's a reimport, move in-library
        files instead of copying.
        """

        if operation != MoveOperation.MOVE and reimport:
            self._log.warning(
                f"Filetote Operation changed to MOVE from {operation} since this is a"
                " reimport."
            )

        if operation == MoveOperation.MOVE or reimport:
            util.move(artifact_source, artifact_dest)
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
            raise AssertionError(f"unknown MoveOperation {operation}")
