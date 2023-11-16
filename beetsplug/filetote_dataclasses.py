""" Dataclasses for Filetote representing Settings/Config-related content along with
data used in processing extra files/artifacts. """

from dataclasses import Field, asdict, dataclass, field, fields
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

FieldType: TypeAlias = Any

if version_info >= (3, 9):
    FieldType = Field[Any]  # type: ignore[misc]


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
        self.validate_types()

    def validate_types(self) -> None:
        """Validate types for FileTote Pairing settings."""
        for field_ in fields(self):
            field_value = getattr(self, field_.name)
            field_type = field_.type

            if field_.name in [
                "enabled",
                "pairing_only",
            ] and not isinstance(field_value, field_type):
                raise TypeError(
                    f'Value for Filetote config key "{field_.name}" should be'
                    f" `{field_type}`, got {type(field_value)}."
                )

            if field_.name == "extensions":
                self._validate_pairing_extensions(field_, field_value)

    def _validate_pairing_extensions(self, field_: FieldType, field_value: Any) -> None:
        if field_value != DEFAULT_ALL_GLOB and not isinstance(field_value, list):
            raise TypeError(
                f'Value for Filetote Pairing config key "{field_.name}" should be the'
                ' glob ".*" (string) or sequence/list of strings (type `List[str]`),'
                f" got {type(field_value)}."
            )

        if field_value != DEFAULT_ALL_GLOB and not all(
            isinstance(elem, str) for elem in field_value
        ):
            for elem in field_value:
                if not isinstance(elem, str):
                    raise TypeError(
                        f'Value for Filetote Pairing config key "{field_.name}" should'
                        " be a sequence/list of strings (type `List[str]`), got"
                        f" {type(elem)}."
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
        self.validate_types()

    def asdict(self) -> dict:  # type: ignore[type-arg]
        """Returns a `dict` version of the dataclass."""
        return asdict(self)

    def adjust(self, attr: str, value: Any) -> None:
        """Adjust provided attribute of class with provided value. For the `pairing`
        property, use the `FiletotePairingData` dataclass and expand the incoming dict
        to arguments."""
        if attr == "pairing":
            value = FiletotePairingData(**value)

        self.validate_types(attr, value)
        setattr(self, attr, value)

    def validate_types(
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
            ] and not isinstance(type(field_value), type(field_type)):
                raise TypeError(
                    f'Value for Filetote config key "{field_.name}" should be'
                    f" `{field_type}`, got {type(field_value)}."
                )

            if field_.name in ["extensions", "filenames", "exclude"]:
                self._validate_str_eq(field_, field_value)

            if field_.name == "patterns":
                self._validate_patterns_dict(field_value)

            if field_.name == "paths":
                self._validate_paths_dict(field_value)

            if field_.name == "print_ignored" and not isinstance(
                field_value, field_type
            ):
                raise TypeError(
                    f'Value for Filetote config key "{field_.name}" should be'
                    f" `{field_type}`, got {type(field_value)}."
                )

    def _validate_str_eq(self, field_: FieldType, field_value: Any) -> None:
        if field_value != DEFAULT_EMPTY and not isinstance(field_value, list):
            raise TypeError(
                f'Value for Filetote config key "{field_.name}" should be a empty'
                " string, an empty list, or sequence/list of strings (type"
                f" `List[str]`), got {type(field_value)}."
            )

        if field_value != DEFAULT_EMPTY and not all(
            isinstance(elem, str) for elem in field_value
        ):
            for elem in field_value:
                if not isinstance(elem, str):
                    raise TypeError(
                        f'Value for Filetote config key "{field_.name}" should be a'
                        " sequence/list of strings (type `List[str]`), got"
                        f" {type(elem)}."
                    )

    def _validate_patterns_dict(self, field_value: Dict[Any, Any]) -> None:
        for key, value in field_value.items():
            if not isinstance(key, str):
                raise TypeError(
                    f'Key "{key}" should be a string (type `str`), got'
                    f" {type(field_value)}."
                )

            if not isinstance(value, List) and all(
                isinstance(elem, str) for elem in value
            ):
                raise TypeError(
                    'Value for Filetote config key "patterns" should be of'
                    f" type `List[str]`, got {type(field_value)}."
                )

    def _validate_paths_dict(self, field_value: Dict[Any, Any]) -> None:
        for key, value in field_value.items():
            if not isinstance(key, str):
                raise TypeError(
                    f'Key "{key}" should be a string (type `str`), got'
                    f" {type(field_value)}."
                )

            if not isinstance(value, Template):
                raise TypeError(
                    'Value for Filetote config key "patterns" should be of'
                    f" type `Template`, got {type(value)}."
                )
