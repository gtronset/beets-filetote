"""Dataclasses for Filetote representing Settings/Config-related content along with
data used in processing extra files/artifacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    TypeAlias,
    get_type_hints,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from beets.library import Library
    from beets.util import MoveOperation

    from .mapping_model import FiletoteMappingModel

StrSeq: TypeAlias = list[str]
OptionalStrSeq: TypeAlias = Literal[""] | StrSeq
PatternsDict: TypeAlias = dict[str, list[str]]
PathBytes: TypeAlias = bytes

DEFAULT_ALL_GLOB: Literal[".*"] = ".*"
DEFAULT_EMPTY: Literal[""] = ""


@dataclass
class FiletoteArtifact:
    """An individual Filetote Artifact item for processing."""

    path: PathBytes
    paired: bool


@dataclass
class FiletoteArtifactCollection:
    """An individual Filetote Item collection for processing."""

    artifacts: list[FiletoteArtifact]
    mapping: FiletoteMappingModel
    source_path: PathBytes
    item_dest: PathBytes


@dataclass
class FiletoteSessionData:
    """Configuration settings for Filetote Item."""

    operation: MoveOperation | None = None
    _beets_lib: Library | None = None
    import_path: PathBytes | None = None

    @property
    def beets_lib(self) -> Library:
        """Ensures the Beets Library is accessible and present."""
        assert self._beets_lib is not None
        return self._beets_lib

    def adjust(self, attr: str, value: Any) -> None:
        """Adjust provided attribute of class with provided value."""
        setattr(self, attr, value)


@dataclass
class FiletoteExcludeData:
    """Configuration settings for Filetote Exclude. Accepts either a sequence/list of
    strings (type `list[str]`, for backwards compatibility) or a dict with `filenames`,
    `extensions`, and/or `patterns` specified.

    `filenames` is intentionally placed first to ensure backwards compatibility.
    """

    filenames: OptionalStrSeq = DEFAULT_EMPTY
    extensions: OptionalStrSeq = DEFAULT_EMPTY
    patterns: PatternsDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validates types upon initialization."""
        self._validate_types()

    def _validate_types(self) -> None:
        """Validate types for Filetote Pairing settings."""
        for field_ in fields(self):
            field_value = getattr(self, field_.name)

            if field_.name in {
                "filenames",
                "extensions",
            }:
                _validate_types_str_seq(
                    ["exclude", field_.name], field_value, DEFAULT_EMPTY
                )

            if field_.name == "patterns":
                _validate_types_dict(
                    ["exclude", field_.name],
                    field_value,
                    field_type=list,
                    list_subtype=str,
                )


@dataclass
class FiletotePairingData:
    """Configuration settings for Filetote Pairing.

    Attributes:
        enabled: Whether `pairing` should apply.
        pairing_only: Override setting to _only_ target paired files.
        extensions: Extensions to target. Defaults to
            _all_ extensions (`.*`).
    """

    enabled: bool = False
    pairing_only: bool = False
    extensions: Literal[".*"] | StrSeq = DEFAULT_ALL_GLOB

    def __post_init__(self) -> None:
        """Validates types upon initialization."""
        self._validate_types()

    def _validate_types(self) -> None:
        """Validate types for Filetote Pairing settings."""
        for field_ in fields(self):
            field_value = getattr(self, field_.name)
            field_type = get_type_hints(FiletotePairingData)[field_.name]

            if field_.name in {
                "enabled",
                "pairing_only",
            }:
                _validate_types_instance(
                    ["pairing", field_.name], field_value, field_type
                )

            if field_.name == "extensions":
                _validate_types_str_seq(
                    ["pairing", field_.name], field_value, DEFAULT_ALL_GLOB
                )


@dataclass
class FiletoteShared:
    """A dataclass for shared artifacts."""

    artifacts: list[PathBytes] = field(default_factory=list)
    mapping_index: int = 0


@dataclass
class FiletoteRun:
    """Holds the state for a single Filetote run within a Beets command."""

    imported_items_paths: dict[int, PathBytes] = field(default_factory=dict)
    process_queue: list[FiletoteArtifactCollection] = field(default_factory=list)
    shared_artifacts: dict[PathBytes, FiletoteShared] = field(default_factory=dict)
    dirs_seen: list[PathBytes] = field(default_factory=list)
    convert_early_import_stages: list[Callable[..., None]] = field(default_factory=list)


@dataclass
class FiletoteConfig:
    """Configuration settings for Filetote Item.

    Attributes:
        session: Beets import session data. Populated once the
            `import_begin` is triggered.
        extensions: List of extensions of artifacts to target.
        filenames: List of filenames of artifacts to target.
        patterns: Dictionary of `glob` pattern-matched patterns
            of artifacts to target.
        exclude: Filenames, extensions, and/or patterns of
            artifacts to exclude.
        pairing: Settings that control whether to look for pairs
            and how to handle them.
        paths: Filetote-level configuration of target queries and
            paths to define how artifact files should be renamed.
        print_ignored: Whether to output lists of ignored artifacts to the
            console as imports finish.
    """

    session: FiletoteSessionData = field(default_factory=FiletoteSessionData)
    extensions: OptionalStrSeq = DEFAULT_EMPTY
    filenames: OptionalStrSeq = DEFAULT_EMPTY
    patterns: PatternsDict = field(default_factory=dict)
    exclude: FiletoteExcludeData = field(default_factory=FiletoteExcludeData)
    pairing: FiletotePairingData = field(default_factory=FiletotePairingData)
    paths: dict[str, str] = field(default_factory=dict)
    print_ignored: bool = False

    def __post_init__(self) -> None:
        """Validates types upon initialization."""
        self._validate_types()

    def asdict(self) -> dict:  # type: ignore[type-arg]
        """Returns a `dict` version of the dataclass."""
        return asdict(self)

    def adjust(self, attr: str, value: Any) -> None:
        """Adjust provided attribute of class with provided value. For the `pairing`
        and `exclude` properties, use the corresponding dataclass and expand the
        incoming value to the proper to arguments.
        """
        if attr == "exclude":
            if isinstance(value, list):
                value = FiletoteExcludeData(value)
            else:
                value = FiletoteExcludeData(**value)

        if attr == "pairing":
            value = FiletotePairingData(**value)

        self._validate_types(attr, value)
        setattr(self, attr, value)

    def _validate_types(
        self, target_field: str | None = None, target_value: Any = None
    ) -> None:
        """Validate types for Filetote Config settings."""
        for field_ in fields(self):
            field_value = target_value or getattr(self, field_.name)
            field_type = get_type_hints(FiletoteConfig)[field_.name]

            if target_field and field_.name != target_field:
                continue

            if field_.name in {
                "exclude",
                "session",
                "pairing",
            }:
                _validate_types_instance([field_.name], field_value, field_type)

            if field_.name in {"extensions", "filenames"}:
                _validate_types_str_seq([field_.name], field_value, DEFAULT_EMPTY)

            if field_.name == "patterns":
                _validate_types_dict(
                    [field_.name], field_value, field_type=list, list_subtype=str
                )

            if field_.name == "paths":
                _validate_types_dict([field_.name], field_value, field_type=str)

            if field_.name == "print_ignored":
                _validate_types_instance([field_.name], field_value, field_type)


def _validate_types_instance(
    field_name: list[str],
    field_value: Any,
    field_type: Any,
) -> None:
    """A simple `instanceof` comparison."""
    if not isinstance(field_value, field_type):
        _raise_type_validation_error(
            field_name,
            field_type,
            field_value,
        )


def _validate_types_dict(
    field_name: list[str],
    field_value: dict[Any, Any],
    field_type: Any,
    list_subtype: Any | None = None,
) -> None:
    for key, value in field_value.items():
        if not isinstance(key, str):
            _raise_type_validation_error(
                field_name,
                "string (`str`)",
                key,
                key_name=key,
            )

        if not isinstance(value, field_type):
            _raise_type_validation_error(field_name, "string (`str`)", value, key, True)

        if list_subtype:
            for elem in value:
                if not isinstance(elem, list_subtype):
                    _raise_type_validation_error(
                        field_name,
                        f"(inner element of the list) {list_subtype}",
                        elem,
                    )


def _validate_types_str_seq(
    field_name: list[str],
    field_value: Any,
    optional_default: str,
) -> None:
    if field_value != optional_default:
        if not isinstance(field_value, list):
            _raise_type_validation_error(
                field_name,
                f"literal `{optional_default}`, an empty list, or sequence/list of"
                " strings (type `list[str]`)",
                field_value,
            )

        for elem in field_value:
            if not isinstance(elem, str):
                _raise_type_validation_error(
                    field_name,
                    "sequence/list of strings (type `list[str]`)",
                    elem,
                )


def _raise_type_validation_error(
    field_name: list[str],
    expected_type: Any,
    value: Any = None,
    key_name: Any | None = None,
    check_keys_value: bool | None = False,
) -> None:
    part_type: str = "Value"
    received_type: Any = type(value)

    if key_name:
        part_type = f'Key "{key_name}"'
        received_type = type(key_name)

    if check_keys_value:
        part_type = f"{part_type}'s Value"
        received_type = type(value)

    raise TypeError(
        f'{part_type} for Filetote config key "{_format_config_hierarchy(field_name)}"'
        f" should be of type {expected_type}, got `{received_type}`"
    )


def _format_config_hierarchy(parts: list[str]) -> str:
    return "".join([f"[{part}]" for part in parts])
