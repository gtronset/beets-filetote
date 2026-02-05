"""beets-filetote plugin for beets."""

from __future__ import annotations

import filecmp
import fnmatch
import os
import re

from sys import version_info
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
)

from beets import config, util
from beets.plugins import BeetsPlugin, find_plugins
from beets.ui import get_path_formats
from beets.util import MoveOperation
from beets.util.functemplate import Template
from mediafile import TYPES as BEETS_FILE_TYPES

from .filetote_dataclasses import (
    FiletoteArtifact,
    FiletoteArtifactCollection,
    FiletoteConfig,
    FiletoteRun,
    FiletoteShared,
    PathBytes,
)
from .mapping_model import FiletoteMappingFormatted, FiletoteMappingModel

# TODO(gtronset): Remove fallback once Beets v2.3 is no longer supported:
# https://github.com/gtronset/beets-filetote/pull/231
# https://github.com/gtronset/beets-filetote/pull/249
try:
    from beets.importer.tasks import MULTIDISC_MARKERS, MULTIDISC_PAT_FMT
    from beets.library.models import DefaultTemplateFunctions
except ImportError:  # fallback for older Beets releases
    from beets.importer import MULTIDISC_MARKERS, MULTIDISC_PAT_FMT
    from beets.library import (
        DefaultTemplateFunctions,
    )

if TYPE_CHECKING:
    from beets.importer import ImportSession, ImportTask
    from beets.library import Item, Library

if version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

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
        """Refresh derived configuration from the current Beets config state."""
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
        dynamically mutates the Item.path (and thus the typical `source`). Without
        grabbing the original `path` here, Filetote would end up looking for artifacts
        in other, then incorrect locations.

        Also runs/initializes any early stages that `convert` provides, if it is loaded.
        """
        self._run_state.imported_items_paths = {
            item.id: item.path for item in task.imported_items()
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
        triggered by Beets, forwarding the event name to the corresponding target
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
        `paths` node. After, then adds any applicable paths from Beets' `path` node,
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

        # Mutate the global BEETS_FILE_TYPES dictionary in-place
        BEETS_FILE_TYPES.update({
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
                BEETS_FILE_TYPES.update({"m4b": "M4B"})

    def _register_session_settings(self, session: ImportSession) -> None:
        """Certain settings are only available and/or finalized once the
        Beets import session begins.
        """
        self.filetote_config.session.adjust("operation", self._import_operation_type())

        import_path: PathBytes | None = None

        if session.paths:
            import_path = os.path.expanduser(session.paths[0])

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
        if not self.filetote_config.session.operation:
            self.filetote_config.session.adjust(
                "operation", self._event_operation_type(event)
            )

        # Needed to in cases where another plugin has overridden the Item.path
        # (ex: `convert`), otherwise, the path is a temp directory.
        if item.id in self._run_state.imported_items_paths:
            imported_item_path: PathBytes = self._run_state.imported_items_paths[
                item.id
            ]
            if imported_item_path != source:
                source = imported_item_path

        # Find and collect all non-media file artifacts
        self.collect_artifacts(item, source, destination)

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
        query_priority: FiletoteQueries = [
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
        if album_path is None:
            raise ValueError(
                f"Could not determine `albumpath` for artifact destination "
                f"for artifact {util.displayable_path(artifact_filename)}."
            )

        # Get template functions and evaluate against mapping
        template_functions = DefaultTemplateFunctions().functions()
        artifact_path = (
            selected_path_template.substitute(mapping_formatted, template_functions)
            + artifact_ext
        )

        replacements = self.filetote_config.session.beets_lib.replacements

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
        mapping_meta |= beets_item.formatted()

        return FiletoteMappingModel(**mapping_meta)

    def _collect_paired_artifacts(
        self, beets_item: Item, source: PathBytes, destination: PathBytes
    ) -> None:
        """Finds and processes paired artifacts for an item in an already-seen
        directory when file "pairing" is enabled. This function looks through available
        artifacts (if the "shared" pool) for potential matching pairs. When found, it
        "claims" any files that are paired with the current item.
        """
        if not self.filetote_config.pairing.enabled:
            return

        source_path: PathBytes = os.path.dirname(source)

        if source_path not in self._run_state.shared_artifacts:
            return

        item_source_filename: PathBytes
        item_source_filename, _ = os.path.splitext(os.path.basename(source))
        artifact_pair_queue: list[FiletoteArtifact] = []
        remaining_shared: list[PathBytes] = []

        # Iterate through shared artifacts to find paired matches
        for artifact_path in self._run_state.shared_artifacts[source_path].artifacts:
            artifact_filename: PathBytes
            artifact_ext: PathBytes
            artifact_filename, artifact_ext = os.path.splitext(
                os.path.basename(artifact_path)
            )
            if (
                artifact_filename == item_source_filename
                and self._is_valid_paired_extension(artifact_ext)
            ):
                artifact_pair_queue.append(
                    FiletoteArtifact(path=artifact_path, paired=True)
                )
            else:
                remaining_shared.append(artifact_path)

        # Update the shared artifacts pool to remove claimed pairs
        self._run_state.shared_artifacts[source_path].artifacts = remaining_shared

        self._update_multimove_artifacts(beets_item, source, destination)

        if artifact_pair_queue:
            self._run_state.process_queue.append(
                FiletoteArtifactCollection(
                    artifacts=artifact_pair_queue,
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
        for index, artifact_collection in enumerate(self._run_state.process_queue):
            artifact_item_dest: PathBytes = artifact_collection.item_dest

            if artifact_item_dest == source:
                self._run_state.process_queue[index] = FiletoteArtifactCollection(
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

    def _discover_artifacts(self, source_path: PathBytes) -> list[PathBytes]:
        """Walks a directory and returns a list of all non-beets-handled files."""
        artifacts: list[PathBytes] = []
        for root, _dirs, files in util.sorted_walk(
            source_path, ignore=config["ignore"].as_str_seq()
        ):
            for filename in files:
                _file_name, file_ext = os.path.splitext(filename)

                # Skip any files extensions handled by beets
                if self._is_beets_file_type(file_ext):
                    continue

                artifacts.append(os.path.join(root, filename))
        return artifacts

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
        source_path: PathBytes = os.path.dirname(source)

        # Check if this path has not already been processed
        if source_path in self._run_state.dirs_seen:
            self._collect_paired_artifacts(beets_item, source, destination)
            return

        # Add this directory to the seen list to avoid re-processing
        self._run_state.dirs_seen.append(source_path)

        # Discover all potential artifacts in the source directory
        discovered_artifacts = self._discover_artifacts(source_path)

        # Classify artifacts as "individual", "paired", or "shared"
        item_source_filename: PathBytes = os.path.splitext(os.path.basename(source))[0]
        queued_artifacts: list[FiletoteArtifact] = []
        shared_artifacts: list[PathBytes] = []

        for artifact_path in discovered_artifacts:
            artifact_filename, artifact_ext = os.path.splitext(
                os.path.basename(artifact_path)
            )

            if not self.filetote_config.pairing.enabled:
                queued_artifacts.append(
                    FiletoteArtifact(path=artifact_path, paired=False)
                )
                continue

            is_paired: bool = (
                artifact_filename == item_source_filename
                and self._is_valid_paired_extension(artifact_ext)
            )

            if is_paired:
                queued_artifacts.append(
                    FiletoteArtifact(path=artifact_path, paired=True)
                )
            else:
                shared_artifacts.append(artifact_path)

        # Organize artifacts for processing
        self._update_multimove_artifacts(beets_item, source, destination)

        shared_mapping_index = len(self._run_state.process_queue)
        self._run_state.shared_artifacts[source_path] = FiletoteShared(
            artifacts=shared_artifacts, mapping_index=shared_mapping_index
        )

        self._run_state.process_queue.append(
            FiletoteArtifactCollection(
                artifacts=queued_artifacts,
                mapping=self._generate_mapping(beets_item, destination),
                source_path=source_path,
                item_dest=destination,
            )
        )

    def process_events(self, lib: Library) -> None:
        """Triggered by the CLI exit event, which itself triggers the processing and
        manipulation of the extra files and artifacts.
        """
        # Ensure destination library settings are accessible
        self.filetote_config.session.adjust("_beets_lib", lib)

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

    def _is_valid_paired_extension(self, artifact_file_ext: str | PathBytes) -> bool:
        return (
            ".*" in self.filetote_config.pairing.extensions
            or util.displayable_path(artifact_file_ext)
            in self.filetote_config.pairing.extensions
        )

    def _is_pattern_match(
        self,
        artifact_relpath: PathBytes,
        patterns_dict: dict[str, list[str]],
        match_category: str | None = None,
    ) -> tuple[bool, str | None]:
        """Check if the file is in the defined patterns."""
        pattern_definitions: list[tuple[str, list[str]]] = list(patterns_dict.items())

        if match_category:
            pattern_definitions = [
                (match_category, self.filetote_config.patterns[match_category])
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

    def _should_process_artifact(
        self,
        source_path: PathBytes,
        artifact_source: PathBytes,
        artifact_filename: PathBytes,
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
        relpath: PathBytes = os.path.relpath(artifact_source, start=source_path)
        artifact_file_ext: str = util.displayable_path(
            os.path.splitext(artifact_filename)[1]
        )

        # "Ignore" if it has already been moved or processed.
        if not os.path.exists(artifact_source):
            self._log.warning(
                f"Artifact {util.displayable_path(artifact_filename)} no longer exists;"
                f" skipping in `_should_process_artifact`."
            )
            return False

        # "Ignore" if it matches an explicit exclusion rule.
        is_exclude_pattern_match, _category = self._is_pattern_match(
            artifact_relpath=relpath,
            patterns_dict=self.filetote_config.exclude.patterns,
        )
        if (
            util.displayable_path(artifact_file_ext)
            in self.filetote_config.exclude.extensions
            or util.displayable_path(artifact_filename)
            in self.filetote_config.exclude.filenames
            or is_exclude_pattern_match
        ):
            return False

        # "Opt-in"and process if any inclusion rule matches.

        matches_filename: bool = (
            util.displayable_path(artifact_filename) in self.filetote_config.filenames
        )
        is_paired: bool = artifact_paired and self._is_valid_paired_extension(
            artifact_file_ext
        )
        matches_pattern: bool = is_pattern_match
        matches_extension: bool = (
            ".*" in self.filetote_config.extensions
            or util.displayable_path(artifact_file_ext)
            in self.filetote_config.extensions
        )

        return matches_filename or is_paired or matches_pattern or matches_extension

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

            is_pattern_match, pattern_category = self._is_pattern_match(
                artifact_relpath=os.path.relpath(artifact_source, start=source_path),
                patterns_dict=self.filetote_config.patterns,
            )

            if not self._should_process_artifact(
                source_path=source_path,
                artifact_source=artifact_source,
                artifact_filename=artifact_filename,
                artifact_paired=artifact.paired,
                is_pattern_match=is_pattern_match,
            ):
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
                self._log.warning(
                    f"Skipping artifact {util.displayable_path(artifact_filename)}"
                    f" because it already exists in the destination."
                )
                ignored_artifacts.append(artifact_filename)
                continue

            artifact_dest = util.unique_path(artifact_dest)
            util.mkdirall(artifact_dest)

            # In copy and link modes, treat reimports specially: move in-library
            # files. (Out-of-library files are copied/moved as usual).
            reimport: bool = self._is_reimport()

            operation: MoveOperation | None = self.filetote_config.session.operation

            self.manipulate_artifact(
                operation, artifact_source, artifact_dest, reimport
            )

            if operation == MoveOperation.MOVE or reimport:
                # Prune vacated directory. Depending on the type of operation,
                # this might be a specific import path, the base library, etc.
                root_path: PathBytes | None = self._get_prune_root_path(
                    source_path, artifact_path
                )

                util.prune_dirs(
                    artifact_path,
                    root=root_path,
                    clutter=config["clutter"].as_str_seq(),
                )

        self.print_ignored_artifacts(ignored_artifacts)

    def print_ignored_artifacts(self, ignored_artifacts: list[PathBytes]) -> None:
        """If enabled in config, output ignored files to beets logs."""
        if self.filetote_config.print_ignored and ignored_artifacts:
            self._log.warning("Ignored files:")
            for artifact_filename in ignored_artifacts:
                self._log.warning("   {0}", os.path.basename(artifact_filename))

    def _is_import_path_same_as_library_dir(
        self, import_path: PathBytes | None, library_dir: PathBytes
    ) -> bool:
        """Checks if the import path matches the library directory."""
        return import_path is not None and import_path == library_dir

    def _is_path_within_ancestry(
        self, child_path: PathBytes | None, parent_path: PathBytes
    ) -> bool:
        """Checks if a path is a subdirectory of another by checking its ancestry."""
        return child_path is not None and parent_path in util.ancestry(child_path)

    def _is_reimport(self) -> bool:
        """Checks if the import is considered a "reimport".

        Copy and link modes treat reimports specially, where in-library files
        are moved.
        """
        library_dir = self.filetote_config.session.beets_lib.directory
        import_path = self.filetote_config.session.import_path

        return self._is_import_path_same_as_library_dir(
            import_path, library_dir
        ) or self._is_path_within_ancestry(
            child_path=import_path, parent_path=library_dir
        )

    def _get_prune_root_path(
        self, source_path: PathBytes, artifact_path: PathBytes
    ) -> PathBytes | None:
        """Deduces the root path for cleaning up dangling files on MOVE.

        This method determines the root path that aids in cleaning up files
        when moving. If the import path matches the library directory or is
        within it, the root path is selected. Otherwise, returns None.
        """
        library_dir = self.filetote_config.session.beets_lib.directory
        import_path = self.filetote_config.session.import_path

        root_path: PathBytes | None = None

        is_multidisc: bool = False

        # Replicate the beets importer's pattern matching for disc folders to determine
        # if this is a multidisc.
        for marker in MULTIDISC_MARKERS:
            p = MULTIDISC_PAT_FMT.replace(b"%s", marker)
            pat = re.compile(p, re.I)
            if pat.match(os.path.basename(source_path)):
                is_multidisc = True

        if import_path is None:
            # If there's not a import path (query, other CLI, etc.), use the Library's
            # dir instead. This is consistent with beet's default pruning for MOVE.
            root_path = library_dir
        elif self._is_import_path_same_as_library_dir(import_path, library_dir):
            # If the import path is the same as the Library's, allow for
            # pruning all the way to the library path.
            root_path = os.path.dirname(library_dir)
        elif self._is_path_within_ancestry(
            child_path=import_path, parent_path=library_dir
        ):
            # If the import path is within the Library's, allow for pruning all the way
            # to the import path.
            root_path = import_path
        elif (
            self._is_path_within_ancestry(
                child_path=artifact_path, parent_path=source_path
            )
            or is_multidisc
        ):
            # If the artifact is within the source path or is multidisc, prune up to the
            # import path.
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
