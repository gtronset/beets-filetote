""" Dataclasses for Filetote representing Settings/Config-related content along with
data used in processing extra files/artifacts. """

from dataclasses import asdict, dataclass, field, fields
from sys import version_info
from typing import Any, Dict, List, Optional, Union

from beets.library import Library
from beets.util import MoveOperation
from beets.util.functemplate import Template

from .mapping_model import FiletoteMappingModel

if version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # type: ignore # pylint: disable=import-error

if version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias  # pylint: disable=import-error

StrSeq: TypeAlias = List[str]
OptionalStrSeq: TypeAlias = Union[Literal[""], StrSeq]

DEFAULT_EMPTY: Literal[""] = ""
DEFAULT_ALL_GLOB: Literal[".*"] = ".*"


@dataclass
class FiletoteArtifact:
    """An individual FileTote Artifact item for processing."""

    path: bytes
    paired: bool


@dataclass
class FiletoteArtifactCollection:
    """An individual FileTote Item collection for processing."""

    artifacts: List[FiletoteArtifact]
    mapping: FiletoteMappingModel
    source_path: bytes


@dataclass
class FiletoteSessionData:
    """Configuration settings for FileTote Item."""

    operation: Optional[MoveOperation] = None
    beets_lib: Optional[Library] = None
    import_path: Optional[bytes] = None

    def adjust(self, attr: str, value: Any) -> None:
        """Adjust provided attribute of class with provided value."""
        setattr(self, attr, value)


@dataclass
class FiletotePairingData:
    """Configuration settings for FileTote Pairing."""

    enabled: bool = False
    pairing_only: bool = False
    extensions: Union[Literal[".*"], StrSeq] = DEFAULT_ALL_GLOB

    def __post_init__(self) -> None:
        self._validate_types()

    def _validate_types(self) -> None:
        """Validate types for FileTote Pairing settings."""
        for field_ in fields(self):
            field_value = getattr(self, field_.name)
            field_type = field_.type

            if field_.name in [
                "enabled",
                "pairing_only",
            ]:
                _validate_types_instance(
                    ["pairing", field_.name], field_value, field_type
                )

            if field_.name == "extensions":
                _validate_types_str_eq(
                    ["pairing", field_.name], field_value, DEFAULT_ALL_GLOB
                )


@dataclass
class FiletoteConfig:
    """Configuration settings for FileTote Item."""

    # pylint: disable=too-many-instance-attributes

    session: FiletoteSessionData = field(default_factory=FiletoteSessionData)
    extensions: OptionalStrSeq = DEFAULT_EMPTY
    filenames: OptionalStrSeq = DEFAULT_EMPTY
    patterns: Dict[str, StrSeq] = field(default_factory=dict)
    exclude: OptionalStrSeq = DEFAULT_EMPTY
    pairing: FiletotePairingData = field(default_factory=FiletotePairingData)
    paths: Dict[str, Template] = field(default_factory=dict)
    print_ignored: bool = False

    def __post_init__(self) -> None:
        self._validate_types()

    def asdict(self) -> dict:  # type: ignore[type-arg]
        """Returns a `dict` version of the dataclass."""
        return asdict(self)

    def adjust(self, attr: str, value: Any) -> None:
        """Adjust provided attribute of class with provided value. For the `pairing`
        property, use the `FiletotePairingData` dataclass and expand the incoming dict
        to arguments."""
        if attr == "pairing":
            value = FiletotePairingData(**value)

        self._validate_types(attr, value)
        setattr(self, attr, value)

    def _validate_types(
        self, target_field: Optional[str] = None, target_value: Any = None
    ) -> None:
        """Validate types for FileTote Config settings."""
        for field_ in fields(self):
            field_value = target_value or getattr(self, field_.name)
            field_type = field_.type

            if target_field and field_.name != target_field:
                continue

            if field_.name in [
                "session",
                "pairing",
            ]:
                _validate_types_instance([field_.name], field_value, field_type)

            if field_.name in ["extensions", "filenames", "exclude"]:
                _validate_types_str_eq([field_.name], field_value, DEFAULT_EMPTY)

            if field_.name == "patterns":
                _validate_types_dict(
                    [field_.name], field_value, field_type=List, list_subtype=str
                )

            if field_.name == "paths":
                _validate_types_dict([field_.name], field_value, field_type=Template)

            if field_.name == "print_ignored":
                _validate_types_instance([field_.name], field_value, field_type)


def _validate_types_instance(
    field_name: List[str],
    field_value: Any,
    field_type: Any,
) -> None:
    """
    A simple `instanceof` comparison. If present, `typewrape` will enable both
    `field_value` and `field_type` to be wrapped by a `type()`.
    """
    if not isinstance(field_value, field_type):
        _raise_type_validation_error(
            field_name,
            field_type,
            field_value,
        )


def _validate_types_dict(
    field_name: List[str],
    field_value: Dict[Any, Any],
    field_type: Any,
    list_subtype: Optional[Any] = None,
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


def _validate_types_str_eq(
    field_name: List[str],
    field_value: Any,
    optional_default: str,
) -> None:
    if field_value != optional_default:
        if not isinstance(field_value, list):
            _raise_type_validation_error(
                field_name,
                f"literal `{optional_default}`, an empty list, or sequence/list of"
                " strings (type `List[str]`)",
                field_value,
            )

        for elem in field_value:
            if not isinstance(elem, str):
                _raise_type_validation_error(
                    field_name,
                    "sequence/list of strings (type `List[str]`)",
                    elem,
                )


def _raise_type_validation_error(
    field_name: List[str],
    expected_type: Any,
    value: Any = None,
    key_name: Optional[Any] = None,
    check_keys_value: Optional[bool] = False,
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


def _format_config_hierarchy(parts: List[str]) -> str:
    return "".join([f"[{part}]" for part in parts])
