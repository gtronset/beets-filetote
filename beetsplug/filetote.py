"""beets-filetote plugin for beets."""

from __future__ import annotations

import filecmp
import fnmatch
import os

from sys import version_info

# Dict, List, and Tuple are needed for py38
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Tuple,
)

from beets import config, util
from beets.library import DefaultTemplateFunctions
from beets.plugins import BeetsPlugin, find_plugins
from beets.ui import get_path_formats
from beets.util import MoveOperation
from beets.util.functemplate import Template
from mediafile import TYPES as BEETS_FILE_TYPES

from .filetote_dataclasses import (
    FiletoteArtifact,
    FiletoteArtifactCollection,
    FiletoteConfig,
    PathBytes,
)
from .mapping_model import FiletoteMappingFormatted, FiletoteMappingModel

if TYPE_CHECKING:
    from beets.importer import ImportSession, ImportTask
    from beets.library import Item, Library

if version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

FiletoteQueries: TypeAlias = List[
    Literal[
        "ext:",
        "filename:",
        "paired_ext:",
        "pattern:",
        "filetote:default",
    ]
]


class FiletotePlugin(BeetsPlugin):
    """Plugin main class. Eventually, should encompass additional features as
    described in https://github.com/beetbox/beets/wiki/Attachments.
    """

    def __init__(self) -> None:
        """Initializes the plugin and sets everything in motion."""
        super().__init__()

        # Set default plugin config settings
        self.config.add(FiletoteConfig().asdict())

        self.filetote: FiletoteConfig = FiletoteConfig(
            extensions=self.config["extensions"].as_str_seq(),
            filenames=self.config["filenames"].as_str_seq(),
            patterns=self.config["patterns"].get(dict),
            paths=self.config["paths"].get(dict),
            print_ignored=self.config["print_ignored"].get(bool),
        )

        if isinstance(self.config["exclude"].get(), (str, list)):
            self.filetote.adjust("exclude", self.config["exclude"].as_str_seq())

            self._log.warning(
                "Deprecation warning: The `exclude` plugin should now use the explicit"
                " settings of `filenames`, `extensions`, and/or `patterns`. See the"
                " `exclude` documentation for more details:"
                " https://github.com/gtronset/beets-filetote#excluding-files"
            )
        else:
            self.filetote.adjust("exclude", self.config["exclude"].get(dict))

        self.filetote.adjust(
            "pairing",
            {
                "enabled": self.config["pairing"]["enabled"].get(bool),
                "pairing_only": self.config["pairing"]["pairing_only"].get(bool),
                "extensions": self.config["pairing"]["extensions"].as_str_seq(),
            },
        )

        queries: FiletoteQueries = [
            "ext:",
            "filename:",
            "paired_ext:",
            "pattern:",
            "filetote:default",
        ]
        path_default: Template = Template("$albumpath/$old_filename")

        self._path_formats: dict[str, Template] = self._get_filetote_path_formats(
            queries, path_default
        )

        self._imported_items_paths: dict[int, PathBytes] = {}
        self._process_queue: list[FiletoteArtifactCollection] = []
        self._shared_artifacts: dict[PathBytes, list[PathBytes]] = {}
        self._dirs_seen: list[PathBytes] = []

        self.early_import_stages = [self._get_imported_items_paths]

        self._convert_early_import_stages: list[Callable[..., None]] = []

        self._register_file_operation_events()

    def _get_imported_items_paths(
        self, session: ImportSession, task: ImportTask
    ) -> None:
        """Registers the original import path for each Items that are potentially
        going to be added to the Library.

        Called as an `early_import_stage` that occurs before other plugin events.

        Organizes into a dictionary that can be later accessible via the Item.id.
        This is needed to accommodate certain plugins such as `convert` which
        dynamically mutates the Item.path (and thus the typical `source`). Without
        grabbing the original `path` here, Filetote would end up looking for artifacts
        in other, then incorrect locations.

        Also runs/initializes any early stages that `convert` provides, if it is loaded.
        """
        self._imported_items_paths = {
            item.id: item.path for item in task.imported_items()
        }

        # If `convert` is not loaded, `self._convert_early_import_stages` is empty
        [
            convert_early_stage(session, task)
            for convert_early_stage in self._convert_early_import_stages
        ]

    def _register_file_operation_events(self) -> None:
        """Registers various file operation events and their corresponding functions.

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
        file_operation_events: list[str] = [
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

        self.register_listener("pluginload", self._register_pluginload_handling)

        self.register_listener("import_begin", self._register_session_settings)

        self.register_listener("cli_exit", self.process_events)

    def _build_file_event_function(self, event: str) -> Callable[..., None]:
        """Creates a function that acts as a wrapper for specific file operation events
        triggered by Beets, forwarding the event name to the corresponding target
        function.
        """

        def file_event_function(**kwargs: Any) -> None:
            self.file_operation_event_listener(event, **kwargs)

        return file_event_function

    def _get_filetote_path_formats(
        self, queries: FiletoteQueries, path_default: Template
    ) -> Dict[str, Template]:
        """Gets all `path` formats from beets and parses those set for Filetote.

        Sets a default value for artifacts, then sets those paths from the Filetote's
        `paths` node. After, then adds any applicable paths from Beets' `path` node,
        unless there's already a representation from Filetote's node to give priority
        to Filetote's definitions.
        """
        path_formats: Dict[str, str | Template] = {"filetote:default": path_default}

        path_formats.update(self.filetote.paths)

        beets_path_query: str
        beets_path_format: Template

        for beets_path_query, beets_path_format in get_path_formats():
            for filetote_query in queries:
                if (
                    beets_path_query.startswith(filetote_query)
                    and beets_path_query not in self.filetote.paths
                ):
                    path_formats[beets_path_query] = beets_path_format

        # Validate all collected paths
        if "ext:.*" in path_formats:
            raise AssertionError(
                "Error: path query `ext:.*` is not valid. If you are trying to"
                " set a default/fallback, please use `filetote:default`"
                " instead."
            )

        # Ensure all returned path queries are a `Template`
        return {
            path_key: self._templatize_path_format(query)
            for path_key, query in path_formats.items()
        }

    def _register_pluginload_handling(self) -> None:
        """This augments the file type list of what is considered a music
        file or media, since MediaFile.TYPES isn't fundamentally a complete
        list of files by extension.
        """
        BEETS_FILE_TYPES.update({
            "m4a": "M4A",
            "wma": "WMA",
            "wave": "WAVE",
        })

        for plugin in find_plugins():
            if plugin.name == "convert":
                convert_early_import_stages = plugin.early_import_stages
                plugin.early_import_stages = []

                self._convert_early_import_stages = convert_early_import_stages

            if plugin.name == "audible":
                BEETS_FILE_TYPES.update({"m4b": "M4B"})

    def _register_session_settings(self, session: ImportSession) -> None:
        """Certain settings are only available and/or finalized once the
        Beets import session begins.
        """
        self.filetote.session.adjust("operation", self._import_operation_type())

        import_path: PathBytes | None = None

        if session.paths:
            import_path = os.path.expanduser(session.paths[0])

        self.filetote.session.import_path = import_path

    def _import_operation_type(self) -> MoveOperation | None:
        """Returns the file manipulations type. This prioritizes `move` over copy if
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

    def _event_operation_type(self, event: str) -> MoveOperation | None:
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

        return mapping.get(event)

    def file_operation_event_listener(
        self, event: str, item: Item, source: PathBytes, destination: PathBytes
    ) -> None:
        """Certain CLI operations such as `move` (`mv`) don't utilize the config file's
        `import` settings which `_operation_type()` uses by default to determine how
        Filetote should move/copy the file. Since there are not otherwise any indicators
        of this, the operation type is inferred based on the event name/type.

        These events should only be emitted in cases where something happens to the
        media files, and this should only have to fall back to infer from event types
        for similar aforementioned CLI commands.
        """
        # Determine the operation type if not already present
        if not self.filetote.session.operation:
            self.filetote.session.adjust("operation", self._event_operation_type(event))

        # Needed to in cases where another plugin has overridden the Item.path
        # (ex: `convert`), otherwise, the path is a temp directory.
        if item.id in self._imported_items_paths:
            imported_item_path: PathBytes = self._imported_items_paths[item.id]
            if imported_item_path != source:
                source = imported_item_path

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
        pattern_category: str | None = None,
    ) -> Template:
        """Calculate the best path query format, prioritizing the below.

        1. `filename:`
        2. `paired_ext:`
        3. `pattern:`
        4. `ext:`
        5. `filetote:default`
        """
        full_filename: str = util.displayable_path(artifact_filename)

        selected_path_query: str | None = None
        selected_path_format: Template | None = None

        for query, path_format in self._path_formats.items():
            filename_prefix: Literal["filename:"] = "filename:"
            paired_ext_prefix: Literal["paired_ext:"] = "paired_ext:"
            pattern_prefix: Literal["pattern:"] = "pattern:"
            ext_prefix: Literal["ext:"] = "ext:"

            if (
                paired
                and query.startswith(paired_ext_prefix)
                and artifact_ext
                == ("." + self.remove_prefix(query, paired_ext_prefix).lstrip("."))
            ):
                # Prioritize `filename:` query selector over `paired_ext:`
                if selected_path_query != filename_prefix:
                    selected_path_query = paired_ext_prefix
                    selected_path_format = path_format
            elif (
                pattern_category
                and not query.startswith((
                    filename_prefix,
                    paired_ext_prefix,
                    ext_prefix,
                ))
                and self.remove_prefix(query, pattern_prefix) == pattern_category
            ):
                # This should pull the corresponding pattern def,
                # Prioritize `filename:` and `paired_ext:` query selector over
                # `pattern:`
                if selected_path_query not in {filename_prefix, paired_ext_prefix}:
                    selected_path_query = pattern_prefix
                    selected_path_format = path_format
            elif query.startswith(ext_prefix) and artifact_ext == (
                "." + self.remove_prefix(query, ext_prefix).lstrip(".")
            ):
                # Prioritize `filename:`, `paired_ext:`, and `pattern:` query selector
                # over `ext:`
                if selected_path_query not in {
                    filename_prefix,
                    paired_ext_prefix,
                    pattern_prefix,
                }:
                    selected_path_query = ext_prefix
                    selected_path_format = path_format
            elif query.startswith(
                filename_prefix
            ) and full_filename == self.remove_prefix(query, filename_prefix):
                selected_path_query = filename_prefix
                selected_path_format = path_format

        # No query matched and no path format provided; use value provided by
        # `filetote:default` which defaults original filename if not present.
        if not selected_path_format:
            selected_path_format = self._path_formats["filetote:default"]

        return selected_path_format

    def _get_artifact_destination(
        self,
        artifact_filename: PathBytes,
        mapping: FiletoteMappingModel,
        paired: bool = False,
        pattern_category: str | None = None,
    ) -> PathBytes:
        """Returns a destination path an artifact/file should be moved to. The
        artifact filename is unique to ensure files aren't overwritten. This also
        checks the config for path formats based on file extension allowing the use of
        beets' template functions. If no path formats are found for the file extension
        the original filename is used with the album path.
        """
        mapping_formatted = FiletoteMappingFormatted(
            mapping, for_path=True, whitelist_replace=["albumpath", "subpath"]
        )

        artifact_ext: str = util.displayable_path(
            os.path.splitext(artifact_filename)[1]
        )

        selected_path_template = self._get_path_query_format_match(
            util.displayable_path(artifact_filename),
            artifact_ext,
            paired,
            pattern_category,
        )

        album_path: str | None = mapping_formatted.get("albumpath")
        # Sanity check for mypy in cases where album_path is None
        assert album_path is not None

        # Get template functions and evaluate against mapping
        template_functions = DefaultTemplateFunctions().functions()
        artifact_path = (
            selected_path_template.substitute(mapping_formatted, template_functions)
            + artifact_ext
        )

        replacements = self.filetote.session.beets_lib.replacements

        # Sanitize filename
        artifact_filename_sanitized: str = util.sanitize_path(
            os.path.basename(artifact_path), replacements
        )
        dirname: str = os.path.dirname(artifact_path)
        artifact_path_sanitized: str = os.path.join(
            dirname, util.displayable_path(artifact_filename_sanitized)
        )

        return util.bytestring_path(artifact_path_sanitized)

    def _templatize_path_format(self, path_format: str | Template) -> Template:
        """Ensures that the path format is a Beets Template."""
        subpath_template: Template

        if isinstance(path_format, Template):
            subpath_template = path_format
        else:
            subpath_template = Template(path_format)

        return subpath_template

    def _generate_mapping(
        self, beets_item: Item, destination: PathBytes
    ) -> FiletoteMappingModel:
        """Creates a mapping of usable path values for renaming. Takes in an
        Item (see https://github.com/beetbox/beets/blob/v2.2.0/beets/library.py#L506).
        """
        album_path: PathBytes = os.path.dirname(destination)

        medianame_old: PathBytes
        medianame_old, _ = os.path.splitext(os.path.basename(beets_item.path))

        medianame_new: PathBytes
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
        self, beets_item: Item, source: PathBytes, destination: PathBytes
    ) -> None:
        """When file "pairing" is enabled, this function looks through available
        artifacts for potential matching pairs. When found, it processes the artifacts
        to be handled specifically as a "pair".
        """
        item_source_filename: PathBytes
        item_source_filename, _ = os.path.splitext(os.path.basename(source))
        source_path: PathBytes = os.path.dirname(source)

        queue_artifacts: list[FiletoteArtifact] = []

        # Check to see if "pairing" is enabled and, if so, check if there are
        # artifacts to look at
        if self.filetote.pairing.enabled and self._shared_artifacts[source_path]:
            # Iterate through shared artifacts to find paired matches
            for artifact_path in self._shared_artifacts[source_path]:
                artifact_filename: PathBytes
                artifact_ext: PathBytes
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

            self._update_multimove_artifacts(beets_item, source, destination)

            if queue_artifacts:
                self._process_queue.append(
                    FiletoteArtifactCollection(
                        artifacts=queue_artifacts,
                        mapping=self._generate_mapping(beets_item, destination),
                        source_path=source_path,
                        item_dest=destination,
                    )
                )

    def _update_multimove_artifacts(
        self, beets_item: Item, source: PathBytes, destination: PathBytes
    ) -> None:
        """Updates all instances of a specific artifact collection in the processing
        queue with a new destination and mapping.

        This is necessary to handle situations where certain operations can actually
        occur twice--the `update` CLI command, for example, first applies an update to
        the Item then to the Album. This ensures the final destination is correctly
        applied for the artifact.
        """
        for index, artifact_collection in enumerate(self._process_queue):
            artifact_item_dest: PathBytes = artifact_collection.item_dest

            if artifact_item_dest == source:
                self._process_queue[index] = FiletoteArtifactCollection(
                    artifacts=artifact_collection.artifacts,
                    mapping=self._generate_mapping(beets_item, destination),
                    source_path=artifact_collection.source_path,
                    item_dest=destination,
                )
                break

    def _is_beets_file_type(self, file_ext: str | PathBytes) -> bool:
        """Checks if the provided file extension is a music file/track
        (i.e., already handles by Beets).
        """
        return (
            len(file_ext) > 1
            and util.displayable_path(file_ext)[1:] in BEETS_FILE_TYPES
        )

    def collect_artifacts(
        self, beets_item: Item, source: PathBytes, destination: PathBytes
    ) -> None:
        """Creates lists of the various extra files and artifacts for processing.
        Since beets passes through the arguments, it's explicitly setting the Item to
        the `item` argument (as it does with the others).

        `source` is a `PathType`, which according to the beets docs:
        > are represented as `PathBytes` objects, in keeping with the Unix filesystem
        > abstraction.
        """
        item_source_filename: PathBytes = os.path.splitext(os.path.basename(source))[0]
        source_path: PathBytes = os.path.dirname(source)

        queue_files: list[FiletoteArtifact] = []

        # Check if this path has not already been processed
        if source_path in self._dirs_seen:
            self._collect_paired_artifacts(beets_item, source, destination)
            return

        non_handled_files: list[PathBytes] = []
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

        self._update_multimove_artifacts(beets_item, source, destination)

        self._process_queue.append(
            FiletoteArtifactCollection(
                artifacts=queue_files,
                mapping=self._generate_mapping(beets_item, destination),
                source_path=source_path,
                item_dest=destination,
            )
        )
        self._dirs_seen.append(source_path)

        self._shared_artifacts[source_path] = non_handled_files

    def process_events(self, lib: Library) -> None:
        """Triggered by the CLI exit event, which itself triggers the processing and
        manipulation of the extra files and artifacts.
        """
        # Ensure destination library settings are accessible
        self.filetote.session.adjust("_beets_lib", lib)

        artifact_collection: FiletoteArtifactCollection
        for artifact_collection in self._process_queue:
            artifacts: list[FiletoteArtifact] = artifact_collection.artifacts

            source_path: PathBytes = artifact_collection.source_path

            if not self.filetote.pairing.pairing_only:
                artifacts.extend(
                    FiletoteArtifact(path=shared_artifact, paired=False)
                    for shared_artifact in self._shared_artifacts[source_path]
                )

            self._shared_artifacts[source_path] = []

            self.process_artifacts(
                source_path=source_path,
                source_artifacts=artifacts,
                mapping=artifact_collection.mapping,
            )

    def _is_valid_paired_extension(self, artifact_file_ext: str | PathBytes) -> bool:
        return (
            ".*" in self.filetote.pairing.extensions
            or util.displayable_path(artifact_file_ext)
            in self.filetote.pairing.extensions
        )

    def _is_pattern_match(
        self,
        artifact_relpath: PathBytes,
        patterns_dict: Dict[str, list[str]],
        match_category: str | None = None,
    ) -> Tuple[bool, str | None]:
        """Check if the file is in the defined patterns."""
        pattern_definitions: list[Tuple[str, list[str]]] = list(patterns_dict.items())

        if match_category:
            pattern_definitions = [
                (match_category, self.filetote.patterns[match_category])
            ]

        for category, patterns in pattern_definitions:
            for pattern in patterns:
                is_match: bool = False

                # This ("/") may need to be changed for Win32
                if pattern.endswith("/"):
                    for path in util.ancestry(artifact_relpath):
                        if not fnmatch.fnmatch(
                            util.displayable_path(path), pattern.strip("/")
                        ):
                            continue
                        is_match = True
                else:
                    is_match = fnmatch.fnmatch(
                        util.displayable_path(artifact_relpath),
                        pattern.lstrip("/"),
                    )

                if is_match:
                    return (is_match, category)

        return (False, None)

    def _is_artifact_ignorable(
        self,
        source_path: PathBytes,
        artifact_source: PathBytes,
        artifact_filename: PathBytes,
        artifact_paired: bool,
    ) -> Tuple[bool, str | None]:
        """Compares the artifact/file to certain checks to see if it should be ignored
        or skipped.
        """
        # Skip/ignore as another plugin or beets has already moved this file
        if not os.path.exists(artifact_source):
            return (True, None)

        relpath: PathBytes = os.path.relpath(artifact_source, start=source_path)

        artifact_file_ext: str = util.displayable_path(
            os.path.splitext(artifact_filename)[1]
        )

        is_exclude_pattern_match: bool
        is_exclude_pattern_match, _category = self._is_pattern_match(
            artifact_relpath=relpath, patterns_dict=self.filetote.exclude.patterns
        )

        # Skip if filename is explicitly in `exclude`
        if (
            util.displayable_path(artifact_file_ext) in self.filetote.exclude.extensions
            or util.displayable_path(artifact_filename)
            in self.filetote.exclude.filenames
            or is_exclude_pattern_match
        ):
            return (True, None)

        # Skip:
        # - extensions not allowed in `extensions`
        # - filenames not explicitly in `filenames`
        # - non-paired files
        # - artifacts not matching patterns

        is_pattern_match: bool
        category: str | None
        is_pattern_match, category = self._is_pattern_match(
            artifact_relpath=relpath, patterns_dict=self.filetote.patterns
        )

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

        matched_category: str | None = None
        if is_pattern_match:
            matched_category = category

        return (False, matched_category)

    def _artifact_exists_in_dest(
        self,
        artifact_source: PathBytes,
        artifact_dest: PathBytes,
    ) -> bool:
        """Checks if the artifact/file already exists in the destination, which would
        also make it ignorable.
        """
        # Skip file
        return os.path.exists(artifact_dest) and filecmp.cmp(
            artifact_source, artifact_dest
        )

    def _get_artifact_subpath(
        self,
        source_path: PathBytes,
        artifact_path: PathBytes,
    ) -> str:
        """Checks if the artifact/file has a subpath in the source location and returns
        its subpath. This also ensures a trailing separator is present if there's a
        subpath. This is needed for renaming and templates as conditionally using the
        `$subpath` is not supported by plugins such as `inline`.
        """
        if artifact_path.startswith(source_path):
            initial_subpath = artifact_path[len(source_path) :].lstrip(
                os.path.sep.encode()
            )
            subpath = util.displayable_path(initial_subpath)

            # Ensures trailing separator is present if needed.
            return (
                subpath + os.path.sep
                if initial_subpath and not subpath.endswith(os.path.sep)
                else subpath
            )

        return ""  # No subpath found

    def process_artifacts(
        self,
        source_path: PathBytes,
        source_artifacts: list[FiletoteArtifact],
        mapping: FiletoteMappingModel,
    ) -> None:
        """Processes and prepares extra files and artifacts for subsequent
        manipulation.
        """
        if not source_artifacts:
            return

        ignored_artifacts: list[PathBytes] = []

        for artifact in source_artifacts:
            artifact_source: PathBytes = artifact.path

            artifact_path: PathBytes = os.path.dirname(artifact_source)

            # os.path.basename() not suitable here as files may be contained
            # within dir of source_path
            artifact_filename: PathBytes = artifact_source[len(artifact_path) + 1 :]

            is_ignorable: bool
            pattern_category: str | None
            is_ignorable, pattern_category = self._is_artifact_ignorable(
                source_path=source_path,
                artifact_source=artifact_source,
                artifact_filename=artifact_filename,
                artifact_paired=artifact.paired,
            )

            if is_ignorable:
                ignored_artifacts.append(artifact_filename)
                continue

            mapping.set(
                "old_filename",
                util.displayable_path(os.path.splitext(artifact_filename)[0]),
            )

            mapping.set(
                "subpath", self._get_artifact_subpath(source_path, artifact_path)
            )

            artifact_dest: PathBytes = self._get_artifact_destination(
                artifact_filename,
                mapping,
                artifact.paired,
                pattern_category,
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

            operation: MoveOperation | None = self.filetote.session.operation

            self.manipulate_artifact(
                operation, artifact_source, artifact_dest, reimport
            )

            if operation == MoveOperation.MOVE or reimport:
                # Prune vacated directory. Depending on the type of operation,
                # this might be a specific import path, the base library, etc.
                root_path: PathBytes | None = self._get_prune_root_path()

                util.prune_dirs(
                    source_path,
                    root=root_path,
                    clutter=config["clutter"].as_str_seq(),
                )

        self.print_ignored_artifacts(ignored_artifacts)

    def print_ignored_artifacts(self, ignored_artifacts: list[PathBytes]) -> None:
        """If enabled in config, output ignored files to beets logs."""
        if self.filetote.print_ignored and ignored_artifacts:
            self._log.warning("Ignored files:")
            for artifact_filename in ignored_artifacts:
                self._log.warning("   {0}", os.path.basename(artifact_filename))

    def _is_import_path_same_as_library_dir(
        self, import_path: PathBytes | None, library_dir: PathBytes
    ) -> bool:
        """Checks if the import path matches the library directory."""
        return import_path is not None and import_path == library_dir

    def _is_import_path_within_library(
        self, import_path: PathBytes | None, library_dir: PathBytes
    ) -> bool:
        """Checks if the import path is within the library directory."""
        return import_path is not None and str(library_dir) in util.ancestry(
            import_path
        )

    def _is_reimport(self) -> bool:
        """Checks if the import is considered a "reimport".

        Copy and link modes treat reimports specially, where in-library files
        are moved.
        """
        library_dir = self.filetote.session.beets_lib.directory
        import_path = self.filetote.session.import_path

        return self._is_import_path_same_as_library_dir(
            import_path, library_dir
        ) or self._is_import_path_within_library(import_path, library_dir)

    def _get_prune_root_path(self) -> PathBytes | None:
        """Deduces the root path for cleaning up dangling files on MOVE.

        This method determines the root path that aids in cleaning up files
        when moving. If the import path matches the library directory or is
        within it, the root path is selected. Otherwise, returns None.
        """
        library_dir = self.filetote.session.beets_lib.directory
        import_path = self.filetote.session.import_path

        root_path: PathBytes | None = None

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
        operation: MoveOperation | None,
        artifact_source: PathBytes,
        artifact_dest: PathBytes,
        reimport: bool | None = False,
    ) -> None:
        """Copy, move, link, hardlink or reflink (depending on `operation`)
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
            raise AssertionError(f"Unknown `MoveOperation`: {operation}")
