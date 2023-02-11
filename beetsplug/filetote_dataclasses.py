""" Dataclasses for Filetote representing Settings/Config-related content along with
data used in processing extra files/artifacts. """

from dataclasses import asdict, dataclass, field
from sys import version_info
from typing import Any, Dict, List, Optional, Union

from beets.library import Library
from beets.util import MoveOperation

from .mapping_model import FiletoteMappingModel

if version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal  # type: ignore # pylint: disable=import-error


@dataclass
class FiletoteArtifact:
    """An individual FileTote Artifact item for processing."""

    path: str
    paired: bool


@dataclass
class FiletoteArtifactCollection:
    """An individual FileTote Item collection for processing."""

    artifacts: List[FiletoteArtifact]
    mapping: FiletoteMappingModel
    source_path: str


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
    extensions: Union[Literal[".*"], List[str]] = ".*"


@dataclass
class FiletoteConfig:
    """Configuration settings for FileTote Item."""

    # pylint: disable=too-many-instance-attributes

    session: FiletoteSessionData = field(default_factory=FiletoteSessionData)
    extensions: Union[Literal[".*"], List[str]] = ".*"
    filenames: Union[Literal[""], List[str]] = ""
    patterns: Dict[str, List[str]] = field(default_factory=dict)
    exclude: Union[Literal[""], List[str]] = ""
    pairing: FiletotePairingData = field(default_factory=FiletotePairingData)
    paths: Dict[str, str] = field(default_factory=dict)
    print_ignored: bool = False

    def asdict(self) -> dict:  # type: ignore[type-arg]
        """Returns a `dict` version of the dataclass."""
        return asdict(self)

    def adjust(self, attr: str, value: Any) -> None:
        """Adjust provided attribute of class with provided value. For the `pairing`
        property, use the `FiletotePairingData` dataclass and expand the incoming dict
        to arguments."""
        if attr == "pairing":
            value = FiletotePairingData(**value)
        setattr(self, attr, value)
