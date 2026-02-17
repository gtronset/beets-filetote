"""beets-filetote plugin for beets."""

from __future__ import annotations

from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeAlias,
)

from beets import config, util
from beets.library.models import DefaultTemplateFunctions
from beets.plugins import BeetsPlugin, find_plugins
from beets.ui import get_path_formats
from beets.util import MoveOperation
from beets.util.functemplate import Template
from mediafile import TYPES as BEETS_FILE_TYPES

from . import path_utils
from .filetote_dataclasses import (
    FiletoteArtifact,
    FiletoteArtifactCollection,
    FiletoteConfig,
    FiletoteRun,
    FiletoteShared,
)
from .mapping_model import FiletoteMappingFormatted, FiletoteMappingModel

if TYPE_CHECKING:
    from collections.abc import Callable

    from beets.importer import ImportSession, ImportTask
    from beets.library import Item, Library

PathBytes: TypeAlias = bytes

FiletotePriorityQueries: TypeAlias = list[
    Literal[
        "ext:",
        "filename:",
        "paired_ext:",
        "pattern:",
    ]
]

# All possible Filetote `query` values for path formats
FiletoteQueries: TypeAlias = list[
    Literal[
        "ext:",
        "filename:",
        "paired_ext:",
        "pattern:",
        "filetote:default",
        "filetote-pairing:default",
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

        # Filetote configuration is set during the `pluginload` event
        self._filetote_config: FiletoteConfig | None = None

        # File types handled by beets, used to check if a file is an artifact
        self._beets_file_types: dict[str, str] = dict(BEETS_FILE_TYPES)

        self._path_queries: FiletoteQueries = [
            "ext:",
            "filename:",
            "paired_ext:",
            "pattern:",
            "filetote:default",
            "filetote-pairing:default",
        ]
        self._path_default: dict[str, str | Template] = {
            "filetote:default": Template("$albumpath/$old_filename"),
            "filetote-pairing:default": Template("$albumpath/$medianame_new"),
        }

        self._run_state: FiletoteRun = FiletoteRun()

        # Register listeners for beets events.
        self.early_import_stages = [self._get_imported_items_paths]
        self._register_file_operation_events()

    @property
    def filetote_config(self) -> FiletoteConfig:
        """The Filetote configuration object.

        This property acts as a guard to ensure that the configuration is
        loaded before it is accessed. It raises a RuntimeError if accessed
        too early.
        """
        if self._filetote_config is None:
            raise RuntimeError("Filetote configuration not yet loaded.")
        return self._filetote_config

    def _refresh_filetote_config(self) -> None:
        """Refresh derived configuration from the current beets config state."""
        # Preserve the existing session data if this is a refresh.
        previous_filetote_config = self._filetote_config
        session_data = (
            previous_filetote_config.session if previous_filetote_config else None
        )

        # Create a new config object with the latest settings.
        filetote = FiletoteConfig(
            extensions=self.config["extensions"].as_str_seq(),
            filenames=self.config["filenames"].as_str_seq(),
            patterns=self.config["patterns"].get(dict),
            paths=self.config["paths"].get(dict),
            print_ignored=self.config["print_ignored"].get(bool),
            duplicate_action=self.config["duplicate_action"].as_str(),
        )

        # Restore the session data to the new config object.
        if session_data:
            filetote.session = session_data

        # Handle the deprecated 'exclude' format.
        exclusion_config = self.config["exclude"]
        exclusion_config_value = exclusion_config.get()
        if isinstance(exclusion_config_value, (str, list)):
            filetote.adjust("exclude", exclusion_config.as_str_seq())
            self._log.warning(
                "Deprecation warning: The `exclude` setting should now use the explicit"
                " settings of `filenames`, `extensions`, and/or `patterns`. See the"
                " `exclude` documentation for more details:"
                " https://github.com/gtronset/beets-filetote#excluding-files"
            )
        else:
            filetote.adjust("exclude", exclusion_config.get(dict))

        # Read the 'pairing' configuration.
        filetote.adjust(
            "pairing",
            {
                "enabled": self.config["pairing"]["enabled"].get(bool),
                "pairing_only": self.config["pairing"]["pairing_only"].get(bool),
                "extensions": self.config["pairing"]["extensions"].as_str_seq(),
            },
        )

        # Update the main plugin attributes.
        self._filetote_config = filetote
        self._path_formats = self._get_filetote_path_formats(
            self._path_queries, self._path_default
        )

    def _get_imported_items_paths(
        self, session: ImportSession, task: ImportTask
    ) -> None:
        """Registers the original import path for each Items that are potentially
        going to be added to the Library.

        Called as an `early_import_stage` that occurs before other plugin events.

        Organizes into a dictionary that can be later accessible via the Item.id.
        This is needed to accommodate certain plugins such as `convert` which
        dynamically mutates the Item.filepath (and thus the typical `source`). Without
        grabbing the original path (`filepath`) here, Filetote would end up looking
        for artifacts in other, then incorrect locations.

        Also runs/initializes any early stages that `convert` provides, if it is loaded.
        """
        self._run_state.imported_items_paths = {
            item.id: item.filepath for item in task.imported_items()
        }

        # If `convert` is not loaded, `self._run_state.convert_early_import_stages` is
        # empty.
        [
            convert_early_stage(session, task)
            for convert_early_stage in self._run_state.convert_early_import_stages
        ]

    def _register_file_operation_events(self) -> None:
        """Registers various file operation events and their corresponding functions.

        This method creates functions for file operation events like moving, copying,
        linking, etc., and registers them as listeners for corresponding beets events.
        It also registers other necessary listeners for plugin functionality
        (`pluginload`, `import_begin`, and `cli_exit`) which do not utilize generated
        function wrappers.

        These functions act as wrappers for beets events, forwarding the event name
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

        file_operation_event_functions: dict[str, Callable[..., None]] = {}

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
        triggered by beets, forwarding the event name to the corresponding target
        function.
        """

        def file_event_function(**kwargs: Any) -> None:
            self.file_operation_event_listener(event, **kwargs)

        return file_event_function

    def _get_filetote_path_formats(
        self, queries: FiletoteQueries, path_default: dict[str, str | Template]
    ) -> dict[str, Template]:
        """Gets all `path` formats from beets and parses those set for Filetote.

        Sets a default value for artifacts, then sets those paths from the Filetote's
        `paths` node. After, then adds any applicable paths from beets' `path` node,
        unless there's already a representation from Filetote's node to give priority
        to Filetote's definitions.
        """
        path_formats: dict[str, str | Template] = path_default

        path_formats |= self.filetote_config.paths

        beets_path_query: str
        beets_path_format: Template

        for beets_path_query, beets_path_format in get_path_formats():
            for filetote_query in queries:
                if (
                    beets_path_query.startswith(filetote_query)
                    and beets_path_query not in self.filetote_config.paths
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
        # Refresh config to capture any changes from other plugins.
        self._refresh_filetote_config()

        self._beets_file_types.update({
            "m4a": "M4A",
            "wma": "WMA",
            "wave": "WAVE",
        })

        for plugin in find_plugins():
            if plugin.name == "convert":
                convert_early_import_stages = plugin.early_import_stages
                if convert_early_import_stages:
                    plugin.early_import_stages = []
                    self._run_state.convert_early_import_stages = (
                        convert_early_import_stages
                    )

            if plugin.name == "audible":
                self._beets_file_types.update({"m4b": "M4B"})

    def _register_session_settings(self, session: ImportSession) -> None:
        """Certain settings are only available and/or finalized once the
        beets import session begins.
        """
        self.filetote_config.session.adjust("operation", self._import_operation_type())

        import_path: Path | None = None

        if session.paths:
            import_path = path_utils.to_path(session.paths[0]).expanduser()

        self.filetote_config.session.import_path = import_path

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
        """Returns the file manipulations type. Requires a beets event to be provided
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
        if not self.filetote_config.session.operation:
            self.filetote_config.session.adjust(
                "operation", self._event_operation_type(event)
            )

        source_path: Path = path_utils.to_path(source)
        destination_path: Path = path_utils.to_path(destination)

        # Needed to in cases where another plugin has overridden the Item.filepath
        # (ex: `convert`), otherwise, the path is a temp directory.
        if item.id in self._run_state.imported_items_paths:
            imported_item_path: Path = self._run_state.imported_items_paths[item.id]
            if imported_item_path != source_path:
                source_path = imported_item_path

        # Find and collect all non-media file artifacts
        self.collect_artifacts(item, source_path, destination_path)

    def _get_path_query_format_match(
        self,
        artifact_filename: str,
        artifact_ext: str,
        paired: bool,
        pattern_category: str | None = None,
    ) -> Template:
        """Selects the best path format for an artifact based on a defined priority.

        This function first finds all matching path queries for the artifact and then
        selects the best one according to the following priority:
        1. `filename:`
        2. `paired_ext:`
        3. `pattern:`
        4. `ext:`

        If no specific rule matches, it returns the `filetote:default` path format,
        unless the file is paired, in which case it returns the
        `filetote-pairing:default`.
        """
        # Priority order of query prefixes for which path format wins when multiple
        # apply.
        query_priority: FiletotePriorityQueries = [
            "filename:",
            "paired_ext:",
            "pattern:",
            "ext:",
        ]

        # Find all applicable path formats for the artifact.
        matches: dict[str, Template] = {}
        for query, path_format in self._path_formats.items():
            if query.startswith(
                "filename:"
            ) and artifact_filename == query.removeprefix("filename:"):
                matches["filename:"] = path_format
            elif (
                query.startswith("paired_ext:")
                and paired
                and artifact_ext == f".{query.removeprefix('paired_ext:').lstrip('.')}"
            ):
                matches["paired_ext:"] = path_format
            elif (
                query.startswith("pattern:")
                and pattern_category
                and query.removeprefix("pattern:") == pattern_category
            ):
                matches["pattern:"] = path_format
            elif (
                query.startswith("ext:")
                and artifact_ext == f".{query.removeprefix('ext:').lstrip('.')}"
            ):
                matches["ext:"] = path_format
            elif (
                pattern_category
                and query == pattern_category
                and not any(query.startswith(prefix) for prefix in query_priority)
            ):
                # Handle prefix-less patterns for backward compatibility with
                # `extrafiles`-style path specifications.
                matches["pattern:"] = path_format

        # Select the best match based on the priority list.
        for query_type in query_priority:
            if query_type in matches:
                return matches[query_type]

        # If no specific rule matched, check if the file is paired and apply
        # default to maintain the pairing.
        if paired:
            return self._path_formats["filetote-pairing:default"]

        # If no specific rule matched, return the default.
        return self._path_formats["filetote:default"]

    def _get_artifact_destination(
        self,
        artifact_filename: str,
        mapping: FiletoteMappingModel,
        paired: bool = False,
        pattern_category: str | None = None,
    ) -> Path:
        """Returns a destination path an artifact/file should be moved to. The
        artifact filename is unique to ensure files aren't overwritten. This also
        checks the config for path formats based on file extension allowing the use of
        beets' template functions. If no path formats are found for the file extension
        the original filename is used with the album path.
        """
        mapping_formatted = FiletoteMappingFormatted(
            mapping, for_path=True, whitelist_replace=["albumpath", "subpath"]
        )

        artifact_ext: str = Path(artifact_filename).suffix

        selected_path_template = self._get_path_query_format_match(
            artifact_filename,
            artifact_ext,
            paired,
            pattern_category,
        )

        album_path: str | None = mapping_formatted.get("albumpath")
        if album_path is None:
            raise ValueError(
                f"Could not determine `albumpath` for artifact destination "
                f"for artifact `{artifact_filename}`."
            )

        # Get template functions and evaluate against mapping
        template_functions = DefaultTemplateFunctions().functions()
        artifact_path = Path(
            selected_path_template.substitute(mapping_formatted, template_functions)
            + artifact_ext
        )

        replacements = self.filetote_config.session.beets_lib.replacements

        # Sanitize filename
        artifact_filename_sanitized: str = util.sanitize_path(
            artifact_path.name, replacements
        )
        dirname: Path = artifact_path.parent
        artifact_path_sanitized: Path = dirname / artifact_filename_sanitized

        return artifact_path_sanitized

    def _templatize_path_format(self, path_format: str | Template) -> Template:
        """Ensures that the path format is a beets Template."""
        subpath_template: Template

        if isinstance(path_format, Template):
            subpath_template = path_format
        else:
            subpath_template = Template(path_format)

        return subpath_template

    def _generate_mapping(
        self, beets_item: Item, destination: Path
    ) -> FiletoteMappingModel:
        """Creates a mapping of usable path values for renaming. Takes in an
        Item (see https://github.com/beetbox/beets/blob/v2.2.0/beets/library.py#L506).
        """
        album_path: Path = destination.parent

        medianame_old: str = beets_item.filepath.stem

        medianame_new: str = Path(destination).stem

        mapping_meta = {
            "albumpath": util.displayable_path(album_path),
            "medianame_old": medianame_old,
            "medianame_new": medianame_new,
        }

        # Include all normal Item fields, using the formatted values
        mapping_meta |= beets_item.formatted()

        return FiletoteMappingModel(**mapping_meta)

    def _collect_paired_artifacts(
        self, beets_item: Item, item_source_path: Path, item_destination_path: Path
    ) -> None:
        """Finds and processes paired artifacts for an item in an already-seen
        directory when file "pairing" is enabled. This function looks through available
        artifacts (if the "shared" pool) for potential matching pairs. When found, it
        "claims" any files that are paired with the current item.
        """
        if not self.filetote_config.pairing.enabled:
            return

        source_path: Path = item_source_path.parent

        if source_path not in self._run_state.shared_artifacts:
            return

        item_source_filename: str = item_source_path.stem
        artifact_pair_queue: list[FiletoteArtifact] = []
        remaining_shared: list[Path] = []

        # Iterate through shared artifacts to find paired matches
        for artifact_path in self._run_state.shared_artifacts[source_path].artifacts:
            artifact_filename: str = artifact_path.stem
            artifact_ext: str = artifact_path.suffix

            is_paired_extension: bool = path_utils.is_allowed_extension(
                artifact_ext, self.filetote_config.pairing.extensions
            )

            if artifact_filename == item_source_filename and is_paired_extension:
                artifact_pair_queue.append(
                    FiletoteArtifact(path=artifact_path, paired=True)
                )
            else:
                remaining_shared.append(artifact_path)

        # Update the shared artifacts pool to remove claimed pairs
        self._run_state.shared_artifacts[source_path].artifacts = remaining_shared

        self._update_multimove_artifacts(
            beets_item, item_source_path, item_destination_path
        )

        if artifact_pair_queue:
            self._run_state.process_queue.append(
                FiletoteArtifactCollection(
                    artifacts=artifact_pair_queue,
                    mapping=self._generate_mapping(beets_item, item_destination_path),
                    source_path=source_path,
                    item_dest=item_destination_path,
                )
            )

    def _update_multimove_artifacts(
        self, beets_item: Item, source: Path, destination: Path
    ) -> None:
        """Updates all instances of a specific artifact collection in the processing
        queue with a new destination and mapping.

        This is necessary to handle situations where certain operations can actually
        occur twice--the `update` CLI command, for example, first applies an update to
        the Item then to the Album. This ensures the final destination is correctly
        applied for the artifact.
        """
        for index, artifact_collection in enumerate(self._run_state.process_queue):
            artifact_item_dest: Path = artifact_collection.item_dest

            if artifact_item_dest == source:
                self._run_state.process_queue[index] = FiletoteArtifactCollection(
                    artifacts=artifact_collection.artifacts,
                    mapping=self._generate_mapping(beets_item, destination),
                    source_path=artifact_collection.source_path,
                    item_dest=destination,
                )
                break

    def collect_artifacts(
        self, beets_item: Item, item_source_path: Path, item_destination_path: Path
    ) -> None:
        """Creates lists of the various extra files and artifacts for processing.
        Since beets passes through the arguments, it's explicitly setting the Item to
        the `item` argument (as it does with the others).
        """
        source_path: Path = item_source_path.parent

        parent_artifacts: list[Path] = []

        if beets_item.disctotal > 1 and path_utils.is_multidisc(source_path):
            multidisc_parent_path: Path = source_path.parent

            self._log.debug(
                f"Directory `{source_path}` matches multi-disc pattern; "
                f"treating parent `{multidisc_parent_path}` as album-level directory."
            )

            disc_specific_ignores: list[str] = path_utils.get_multidisc_ignore_paths(
                multidisc_parent_path
            )

            if multidisc_parent_path not in self._run_state.dirs_seen:
                # Add this directory to the seen list to avoid re-processing
                self._run_state.dirs_seen.append(multidisc_parent_path)

                parent_artifacts = path_utils.discover_artifacts(
                    source_path=multidisc_parent_path,
                    ignore=config["ignore"].as_str_seq() + disc_specific_ignores,
                    beets_file_types=self._beets_file_types,
                )

        local_artifacts: list[Path] = []

        # Check if this path has not already been processed
        if source_path in self._run_state.dirs_seen:
            self._collect_paired_artifacts(
                beets_item, item_source_path, item_destination_path
            )

            if not parent_artifacts:
                return
        else:
            # Add this directory to the seen list to avoid re-processing
            self._run_state.dirs_seen.append(source_path)

            local_artifacts = path_utils.discover_artifacts(
                source_path=source_path,
                ignore=config["ignore"].as_str_seq(),
                beets_file_types=self._beets_file_types,
            )

        discovered_artifacts: list[Path] = local_artifacts + parent_artifacts

        # Classify artifacts as "individual", "paired", or "shared"
        item_source_filename: str = item_source_path.stem
        queued_artifacts: list[FiletoteArtifact] = []
        shared_artifacts: list[Path] = []

        for artifact_path in discovered_artifacts:
            artifact_filename: str = artifact_path.stem
            artifact_ext: str = artifact_path.suffix

            if not self.filetote_config.pairing.enabled:
                queued_artifacts.append(
                    FiletoteArtifact(path=artifact_path, paired=False)
                )
                continue

            is_paired_extension: bool = path_utils.is_allowed_extension(
                artifact_ext, self.filetote_config.pairing.extensions
            )

            is_paired: bool = (
                artifact_filename == item_source_filename and is_paired_extension
            )

            if is_paired:
                queued_artifacts.append(
                    FiletoteArtifact(path=artifact_path, paired=True)
                )
            else:
                shared_artifacts.append(artifact_path)

        # Organize artifacts for processing
        self._update_multimove_artifacts(
            beets_item, item_source_path, item_destination_path
        )

        shared_mapping_index = len(self._run_state.process_queue)
        self._run_state.shared_artifacts[source_path] = FiletoteShared(
            artifacts=shared_artifacts, mapping_index=shared_mapping_index
        )

        self._run_state.process_queue.append(
            FiletoteArtifactCollection(
                artifacts=queued_artifacts,
                mapping=self._generate_mapping(beets_item, item_destination_path),
                source_path=source_path,
                item_dest=item_destination_path,
            )
        )

    def process_events(self, lib: Library) -> None:
        """Triggered by the CLI exit event, which itself triggers the processing and
        manipulation of the extra files and artifacts.
        """
        # Ensure destination library settings are accessible
        self.filetote_config.session.adjust("_beets_lib", lib)
        # Make the library path easier to access
        self.filetote_config.session.adjust(
            "_library_path", path_utils.to_path(lib.directory)
        )

        # Process paired artifacts if they exist
        for artifact_collection in self._run_state.process_queue:
            if artifact_collection.artifacts:
                self.process_artifacts(
                    source_path=artifact_collection.source_path,
                    source_artifacts=artifact_collection.artifacts,
                    mapping=artifact_collection.mapping,
                )

        # Handle all shared artifacts for each source directory
        if not self.filetote_config.pairing.pairing_only:
            for (
                source_path,
                shared_artifacts,
            ) in self._run_state.shared_artifacts.items():
                if not shared_artifacts.artifacts:
                    continue

                # Mapping derives from the first Item that found this source path
                album_level_mapping = self._run_state.process_queue[
                    shared_artifacts.mapping_index
                ].mapping

                artifacts_to_process = [
                    FiletoteArtifact(path=shared_artifact, paired=False)
                    for shared_artifact in shared_artifacts.artifacts
                ]

                self.process_artifacts(
                    source_path=source_path,
                    source_artifacts=artifacts_to_process,
                    mapping=album_level_mapping,
                )

    def _should_process_artifact(
        self,
        source_path: Path,
        artifact_source: Path,
        artifact_paired: bool,
        is_pattern_match: bool = False,
    ) -> bool:
        """Decides if an artifact should be processed based on inclusion rules.

        This function implements the core "opt-in" logic for Filetote. An artifact
        is ignored by default unless it meets specific criteria. It first checks for
        explicit exclusion rules. If none apply, it then checks against a series of
        inclusion rules. The artifact will be processed if it matches at least one
        inclusion rule.
        """
        artifact_filename: str = artifact_source.name
        artifact_file_ext: str = artifact_source.suffix

        # "Ignore" if it has already been moved or processed.
        if not Path(artifact_source).exists():
            self._log.warning(
                f"Artifact `{artifact_filename}` no longer exists;"
                f" skipping in `_should_process_artifact`."
            )
            return False

        # "Ignore" if it matches an explicit exclusion rule.
        is_exclude_pattern_match, _category = path_utils.is_pattern_match(
            artifact_relpath=artifact_source.relative_to(source_path),
            patterns_dict=self.filetote_config.exclude.patterns,
        )
        if (
            artifact_file_ext in self.filetote_config.exclude.extensions
            or artifact_filename in self.filetote_config.exclude.filenames
            or is_exclude_pattern_match
        ):
            return False

        # "Opt-in" and process if any inclusion rule matches.

        matches_filename: bool = artifact_filename in self.filetote_config.filenames

        is_paired_extension: bool = path_utils.is_allowed_extension(
            artifact_file_ext, self.filetote_config.pairing.extensions
        )
        is_paired: bool = artifact_paired and is_paired_extension

        matches_pattern: bool = is_pattern_match
        matches_extension: bool = path_utils.is_allowed_extension(
            artifact_file_ext, self.filetote_config.extensions
        )

        return matches_filename or is_paired or matches_pattern or matches_extension

    def process_artifacts(
        self,
        source_path: Path,
        source_artifacts: list[FiletoteArtifact],
        mapping: FiletoteMappingModel,
    ) -> None:
        """Processes and prepares extra files and artifacts for subsequent
        manipulation.
        """
        if not source_artifacts:
            return

        ignored_artifacts: list[Path] = []

        for artifact in source_artifacts:
            artifact_source: Path = artifact.path

            artifact_filename: str = artifact_source.name

            is_pattern_match, pattern_category = path_utils.is_pattern_match(
                artifact_relpath=artifact_source.relative_to(source_path),
                patterns_dict=self.filetote_config.patterns,
            )

            if not self._should_process_artifact(
                source_path=source_path,
                artifact_source=artifact_source,
                artifact_paired=artifact.paired,
                is_pattern_match=is_pattern_match,
            ):
                ignored_artifacts.append(artifact_source)
                continue

            mapping.set(
                "old_filename",
                artifact_source.stem,
            )

            mapping.set(
                "subpath", path_utils.get_artifact_subpath(source_path, artifact_source)
            )

            artifact_dest: Path = self._get_artifact_destination(
                artifact_filename,
                mapping,
                artifact.paired,
                pattern_category,
            )

            if artifact_source == artifact_dest:
                self._log.debug(
                    f"Source and destination are the same ({artifact_source}); "
                    f"skipping artifact processing."
                )
                continue

            artifact_dest_unique: bytes = util.bytestring_path(artifact_dest)
            should_replace: bool = self.filetote_config.duplicate_action == "remove"

            if artifact_dest.exists():
                action = self.filetote_config.duplicate_action

                # "merge" (Default) and backwards-compatible logic.
                if action == "merge":
                    if path_utils.artifact_exists_in_dest(
                        artifact_source=artifact_source,
                        artifact_dest=artifact_dest,
                    ):
                        action = "skip"
                    else:
                        action = "keep"

                match action:
                    case "remove":
                        pass
                    case "skip":
                        self._log.debug(
                            f"Skipping artifact `{artifact_filename}`"
                            f" because it already exists in the destination."
                        )
                        ignored_artifacts.append(artifact_source)
                        continue
                    case _:
                        # Keep both old and new artifacts, giving new artifact name
                        # uniqueness (e.g., "file.1.txt")
                        artifact_dest_unique = util.unique_path(artifact_dest_unique)

            artifact_dest.parent.mkdir(parents=True, exist_ok=True)

            # In copy and link modes, treat reimports specially: move in-library
            # files. (Out-of-library files are copied/moved as usual).
            is_reimport: bool = path_utils.is_reimport(
                self.filetote_config.session.library_path,
                self.filetote_config.session.import_path,
            )

            operation: MoveOperation | None = self.filetote_config.session.operation

            self.manipulate_artifact(
                operation,
                util.bytestring_path(artifact_source),
                artifact_dest_unique,
                is_reimport,
                should_replace,
            )

            artifact_parent: Path = artifact_source.parent

            if operation == MoveOperation.MOVE or is_reimport:
                # Prune vacated directory. Depending on the type of operation,
                # this might be a specific import path, the base library, etc.
                root_path: Path | None = path_utils.get_prune_root_path(
                    source_path,
                    artifact_parent,
                    self.filetote_config.session.library_path,
                    self.filetote_config.session.import_path,
                )

                util.prune_dirs(
                    artifact_parent,
                    root=root_path,
                    clutter=config["clutter"].as_str_seq(),
                )

        self.print_ignored_artifacts(ignored_artifacts)

    def print_ignored_artifacts(self, ignored_artifacts: list[Path]) -> None:
        """If enabled in config, output ignored files to beets logs."""
        if self.filetote_config.print_ignored and ignored_artifacts:
            self._log.warning("Ignored files:")
            for artifact in ignored_artifacts:
                self._log.warning(f"   {artifact.name}")

    def manipulate_artifact(
        self,
        operation: MoveOperation | None,
        artifact_source: PathBytes,
        artifact_dest: PathBytes,
        is_reimport: bool = False,
        replace: bool = False,
    ) -> None:
        """Copy, move, link, hardlink or reflink (depending on `operation`)
        the artifacts (as well as write metadata).
        NOTE: `operation` should be an instance of `MoveOperation`.

        If the operation is copy or a link but it's a reimport, move in-library
        files instead of copying.
        """
        if operation != MoveOperation.MOVE and is_reimport:
            self._log.warning(
                f"Filetote Operation changed to MOVE from {operation} since this is a"
                " reimport."
            )

        if operation == MoveOperation.MOVE or is_reimport:
            util.move(artifact_source, artifact_dest, replace=replace)
        elif operation == MoveOperation.COPY:
            util.copy(artifact_source, artifact_dest, replace=replace)
        elif operation == MoveOperation.LINK:
            util.link(artifact_source, artifact_dest, replace=replace)
        elif operation == MoveOperation.HARDLINK:
            util.hardlink(artifact_source, artifact_dest, replace=replace)
        elif operation == MoveOperation.REFLINK:
            util.reflink(
                artifact_source, artifact_dest, replace=replace, fallback=False
            )
        elif operation == MoveOperation.REFLINK_AUTO:
            util.reflink(artifact_source, artifact_dest, replace=replace, fallback=True)
        else:
            raise AssertionError(f"Unknown `MoveOperation`: {operation}")
